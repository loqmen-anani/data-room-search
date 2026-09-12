import re
from datetime import date

from dataroom.indexer import DURATION_HEADING, DataRoomIndex, plain, tokenize
from dataroom.models import (
    ArticleHit,
    Chunk,
    Contract,
    ContractHit,
    DateRange,
    Filters,
    SearchRequest,
    SearchResponse,
)

MAX_ARTICLES_PER_CONTRACT = 3
EXCERPT_CHARS = 400

# Quand un filtre porte sur un champ, l'article qui le justifie est remonté même sans query (DURATION_HEADING pour les dates).
LAW_HEADING = re.compile(r"LOI APPLICABLE|GOVERNING LAW|JURIDICTION")


class Unknown(Exception):
    """Le champ filtré est vide sur ce contrat : on ne peut ni l'inclure ni l'exclure."""


def _active(rng: DateRange | None) -> bool:
    return rng is not None and (rng.after is not None or rng.before is not None)


def _law_active(f: Filters) -> bool:
    return f.governing_law is not None and bool(f.governing_law.in_ or f.governing_law.not_in)


def _check_range(label: str, value: date | None, rng: DateRange) -> str | None:
    """Renvoie la description du filtre s'il passe, None s'il échoue, lève Unknown si la date manque."""
    if value is None:
        raise Unknown
    if rng.after and value < rng.after or rng.before and value > rng.before:
        return None
    bounds = [f">= {rng.after}" if rng.after else "", f"<= {rng.before}" if rng.before else ""]
    return f"{label} {value} ({' et '.join(b for b in bounds if b)})"


def apply_filters(c: Contract, f: Filters) -> list[str] | None:
    """Liste des filtres satisfaits, ou None si le contrat est exclu. Lève Unknown si un champ filtré est vide."""
    matched = []
    if f.entity_ids:
        if not set(f.entity_ids) <= c.entity_ids:
            return None
        matched.append("parties: " + ", ".join(f.entity_ids))
    if f.contract_types:
        if c.contract_type not in f.contract_types:
            return None
        matched.append(f"type: {c.contract_type}")
    if _law_active(f):
        if c.governing_law is None:
            raise Unknown
        if f.governing_law.in_ and c.governing_law not in f.governing_law.in_:
            return None
        if f.governing_law.not_in and c.governing_law in f.governing_law.not_in:
            return None
        matched.append(f"loi applicable: {c.governing_law}")
    for label, value, rng in (("signature", c.signature_date, f.signature_date), ("fin", c.end_date, f.end_date)):
        if not _active(rng):
            continue
        desc = _check_range(label, value, rng)
        if desc is None:
            return None
        matched.append(desc)
    return matched


def _excluded_by_amendment(c: Contract, f: Filters) -> bool:
    """Exclu, mais passerait (ou serait indéterminé) avec sa date de fin d'origine : c'est un avenant qui l'écarte."""
    if c.end_date == c.initial_end_date or not _active(f.end_date):
        return False
    try:
        return apply_filters(c.model_copy(update={"end_date": c.initial_end_date}), f) is not None
    except Unknown:
        return True


def _filter_articles(index: DataRoomIndex, c: Contract, f: Filters) -> list[Chunk]:
    """Articles qui justifient les filtres : DURÉE (y compris celle des avenants du contrat), LOI APPLICABLE."""
    dates = _active(f.signature_date) or _active(f.end_date)
    wanted = [p for p, on in ((DURATION_HEADING, dates), (LAW_HEADING, _law_active(f))) if on]
    own = [ch for ch in index.contract_chunks(c.contract_id) if any(p.search(plain(ch.heading)) for p in wanted)]
    amending = [ch for a in c.amended_by for ch in index.contract_chunks(a) if DURATION_HEADING.search(plain(ch.heading))]
    return own + (amending if dates else [])


def _hit(chunk: Chunk, score: float | None) -> ArticleHit:
    text = chunk.text if len(chunk.text) <= EXCERPT_CHARS else chunk.text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + " […]"
    return ArticleHit(chunk_id=chunk.chunk_id, heading=chunk.heading, excerpt=text,
                      score=None if score is None else round(score, 3))


def _check_known(label: str, values: list[str] | None, known: set[str]) -> None:
    """Une valeur absente de la data room est une erreur (faute de frappe, entité inexistante), pas un filtre vide."""
    unknown = sorted(set(values or ()) - known)
    if unknown:
        raise ValueError(f"{label} inconnu(s) : {', '.join(unknown)}. Valeurs possibles : {', '.join(sorted(known))}.")


def search(index: DataRoomIndex, req: SearchRequest) -> SearchResponse:
    f = req.filters
    _check_known("entity_ids", f.entity_ids, index.entities)
    _check_known("contract_types", f.contract_types, index.contract_types)
    if f.governing_law:
        _check_known("governing_law", (f.governing_law.in_ or []) + (f.governing_law.not_in or []), index.laws)
    query_tokens = tokenize(req.query) if req.query else []
    if req.query and not query_tokens:
        raise ValueError(f"query sans terme recherchable (mots vides seulement) : {req.query!r}. "
                         "Reformuler avec des mots du contrat, ou omettre la query.")

    # 1. Pré-filtrage sur les métadonnées
    candidates: list[tuple[Contract, list[str]]] = []
    excluded_unknown = []
    excluded_by_amendment = {}
    for c in index.contracts.values():
        try:
            matched = apply_filters(c, f)
        except Unknown:
            excluded_unknown.append(c.contract_id)
            continue
        if matched is not None:
            candidates.append((c, matched))
        elif _excluded_by_amendment(c, f):
            excluded_by_amendment[c.contract_id] = (
                f"fin {c.initial_end_date or 'non renseignée'} → {c.end_date} (avenant {', '.join(c.amended_by)})"
            )

    results = []
    for c, matched in candidates:
        chunk_idxs = index.chunks_by_contract.get(c.contract_id, [])

        # 2. Classement BM25 des articles du contrat (uniquement si query)
        articles: list[ArticleHit] = []
        score = None
        if query_tokens:
            scored = sorted(((index.bm25.score(query_tokens, i), index.chunks[i]) for i in chunk_idxs),
                            key=lambda x: x[0], reverse=True)
            scored = [(s, ch) for s, ch in scored if s > 0]
            if not scored:
                continue  # aucun article ne parle de la query
            score = round(scored[0][0], 3)  # score du contrat = son meilleur article
            articles = [_hit(ch, s) for s, ch in scored[:MAX_ARTICLES_PER_CONTRACT]]

        # 3. Articles justifiant les filtres (DURÉE, LOI APPLICABLE…)
        seen = {a.chunk_id for a in articles}
        articles += [_hit(ch, None) for ch in _filter_articles(index, c, f) if ch.chunk_id not in seen]

        results.append(ContractHit(
            **c.model_dump(include={"contract_id", "filename", "title", "parties", "contract_type",
                                    "signature_date", "end_date", "governing_law"}),
            amends=c.amends or None,
            amended_by=c.amended_by or None,
            warnings=c.warnings or None,
            matched_filters=matched,
            relevant_articles=articles,
            score=score,
        ))

    # 4. Sans query : tous les candidats (exhaustif). Avec query : top_k par pertinence.
    if query_tokens:
        results = sorted(results, key=lambda r: r.score, reverse=True)[: req.top_k]
    return SearchResponse(total_candidates=len(candidates), excluded_unknown=excluded_unknown,
                          excluded_by_amendment=excluded_by_amendment, results=results)
