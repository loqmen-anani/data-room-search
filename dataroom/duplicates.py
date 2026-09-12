"""Détection des doublons probables : fichier téléversé deux fois, version signée et non signée, traduction de courtoisie.

Deux contrats sont candidats s'ils ont les mêmes parties, ne sont pas un contrat et son avenant, et soit décrivent le
même acte (même type et une date commune), soit ont un texte quasi identique. Le regroupement par jeu de parties limite
les comparaisons à chaque groupe : la data room peut compter des milliers de contrats.
"""

from itertools import combinations

from dataroom.indexer import DataRoomIndex, tokenize
from dataroom.models import Contract, DuplicatePair, DuplicatesResponse, FindDuplicates
from dataroom.search import check_known

NEAR_IDENTICAL = 0.8  # similarité de Jaccard à partir de laquelle deux textes sont considérés comme le même document


def text_similarity(a: set[str], b: set[str]) -> float:
    """Jaccard sur les mots des deux textes : 1 = mêmes mots, 0 = aucun mot commun."""
    return len(a & b) / len(a | b) if a or b else 0.0


def _reasons(a: Contract, b: Contract, similarity: float) -> list[str]:
    """Indices d'un doublon ; les dates comparées sont celles des métadonnées, avant avenants."""
    reasons = ["mêmes parties"]
    if a.contract_type == b.contract_type:
        reasons.append(f"même type ({a.contract_type})")
    if a.signature_date and a.signature_date == b.signature_date:
        reasons.append(f"même date de signature ({a.signature_date})")
    if a.initial_end_date and a.initial_end_date == b.initial_end_date:
        reasons.append(f"même date de fin ({a.initial_end_date})")
    if similarity >= NEAR_IDENTICAL:
        reasons.append(f"texte identique à {round(similarity * 100)} %")
    return reasons


def is_duplicate(a: Contract, b: Contract, similarity: float) -> bool:
    if a.contract_id in b.amends or b.contract_id in a.amends:
        return False  # un contrat et son avenant, pas un doublon
    reasons = _reasons(a, b, similarity)
    same_act = any(r.startswith("même type") for r in reasons) and any(r.startswith("même date") for r in reasons)
    return same_act or similarity >= NEAR_IDENTICAL


def find_duplicates(index: DataRoomIndex, params: FindDuplicates) -> DuplicatesResponse:
    check_known("entity_ids", params.entity_ids, index.entities)
    wanted = set(params.entity_ids or ())
    contracts = [c for c in index.contracts.values() if c.entity_ids and wanted <= c.entity_ids]

    groups: dict[frozenset[str], list[Contract]] = {}
    for c in contracts:
        groups.setdefault(frozenset(c.entity_ids), []).append(c)

    words = {c.contract_id: set(tokenize(c.content)) for c in contracts}
    pairs = []
    for group in groups.values():
        for a, b in combinations(group, 2):
            similarity = text_similarity(words[a.contract_id], words[b.contract_id])
            if is_duplicate(a, b, similarity):
                pairs.append(DuplicatePair(
                    contract_ids=[a.contract_id, b.contract_id],
                    titles=[a.title, b.title],
                    parties=sorted(a.entity_ids),
                    reasons=_reasons(a, b, similarity),
                    text_similarity=round(similarity, 2),
                ))
    pairs.sort(key=lambda p: p.text_similarity, reverse=True)
    return DuplicatesResponse(contracts_compared=len(contracts), pairs=pairs)
