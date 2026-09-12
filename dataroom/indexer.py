"""Indexation de la data room : découpage par article + index BM25.

Usage : python -m dataroom.indexer [chemin/vers/data_room.json]
"""

import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

from dataroom.config import DATA_PATH
from dataroom.loader import dates_in_text, load_contracts
from dataroom.models import Chunk, Contract

# "ARTICLE 6 — DURÉE" (tiret cadratin, demi-cadratin ou simple)
ARTICLE_RE = re.compile(r"^ARTICLE\s+\d+\s*[—–-].*$", re.MULTILINE)

# Sur un texte passé par `plain` : article qui fixe le terme (« DURÉE », « REPORT DU TERME », « TERM »), et contrat qui
# en modifie un autre. Frontières de mot : « DÉTERMINATION DU PRIX » ou « TERMINATION » ne sont pas des articles de durée.
DURATION_HEADING = re.compile(r"\b(DUREE|PROROGATION|TERME?|TERMS?)\b")
AMENDMENT_RE = re.compile(r"\b(AVENANTS?|AMENDMENTS?)\b")

STOPWORDS = set("""
au aux avec ce ces dans de des du elle en et eux il je la le les leur lui ma mais me meme mes moi mon ne nos
notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous
est sont ete etre avoir a ont sera seront tout toute tous toutes cette cet leurs dont ainsi
the of and to in a an by for or be shall this with within
""".split())


# --- Découpage ----------------------------------------------------------------

def chunk_contract(contract: Contract) -> list[Chunk]:
    """Un chunk par article. Le texte avant le premier article devient le PRÉAMBULE."""
    text = contract.content
    starts = [m.start() for m in ARTICLE_RE.finditer(text)]
    sections = []
    if not starts or text[: starts[0]].strip():
        sections.append(("PRÉAMBULE", text[: starts[0]] if starts else text))
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        heading, _, body = text[start:end].partition("\n")
        sections.append((heading.strip(), body))
    return [
        Chunk(chunk_id=f"{contract.contract_id}-{i}", contract_id=contract.contract_id, heading=heading, text=body.strip())
        for i, (heading, body) in enumerate(sections)
        if body.strip()
    ]


# --- Tokenisation -------------------------------------------------------------

def plain(text: str) -> str:
    """Majuscules sans accents, pour comparer des titres : « Durée » -> « DUREE »."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()


def tokenize(text: str) -> list[str]:
    s = plain(text).lower()
    tokens = []
    for tok in re.findall(r"[a-z0-9]+", s):
        if len(tok) < 2 or tok in STOPWORDS:
            continue
        if len(tok) > 3 and tok[-1] in "sx":  # pluriel : "contrats" -> "contrat"
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


# --- BM25 ---------------------------------------------------------------------

class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg_len = sum(self.lens) / len(docs) if docs else 0.0
        df = Counter(tok for d in docs for tok in set(d))
        n = len(docs)
        self.idf = {tok: math.log(1 + (n - f + 0.5) / (f + 0.5)) for tok, f in df.items()}

    def score(self, query: list[str], doc_idx: int) -> float:
        tf, length = self.tfs[doc_idx], self.lens[doc_idx]
        total = 0.0
        for tok in query:
            f = tf.get(tok, 0)
            if f:
                total += self.idf[tok] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg_len))
        return total


# --- Index --------------------------------------------------------------------

class DataRoomIndex:
    def __init__(self, contracts: list[Contract]):
        self.contracts = {c.contract_id: c for c in contracts}
        self.chunks = [ch for c in contracts for ch in chunk_contract(c)]
        self.chunks_by_contract: dict[str, list[int]] = {}
        for i, ch in enumerate(self.chunks):
            self.chunks_by_contract.setdefault(ch.contract_id, []).append(i)
        self._link_amendments()
        # Enrichissement contextuel : titre et parties indexés avec chaque article.
        self.bm25 = BM25([tokenize(self._contextualize(ch)) for ch in self.chunks])
        # Valeurs présentes dans la data room : proposées au LLM dans le schéma du tool, seules acceptées en filtre.
        self.entities = {e for c in contracts for e in c.entity_ids}
        self.contract_types = {c.contract_type for c in contracts}
        self.laws = {c.governing_law for c in contracts if c.governing_law}

    def contract_chunks(self, contract_id: str) -> list[Chunk]:
        return [self.chunks[i] for i in self.chunks_by_contract.get(contract_id, [])]

    def _link_amendments(self) -> None:
        """Rattache chaque avenant au contrat qu'il modifie et reporte le terme qu'il fixe.

        Contrat modifié : mêmes parties, signé avant l'avenant, et dont la date de signature est citée dans l'avenant
        (à défaut, le seul contrat possible). Nouveau terme : dernière date citée dans l'article DURÉE / PROROGATION /
        TERME de l'avenant, à défaut la date de fin de l'avenant ; si les deux existent et diffèrent, l'avenant porte un
        avertissement. Sans article de durée, l'avenant ne touche pas au terme (avenant de prix, par exemple).
        Sans contrat identifié, l'avenant reste isolé, avec un avertissement.
        """
        amendments = [c for c in self.contracts.values() if AMENDMENT_RE.search(plain(f"{c.contract_type} {c.title}"))]
        amendment_ids = {a.contract_id for a in amendments}
        for a in sorted(amendments, key=lambda a: a.signature_date or date.min):
            candidates = [
                c for c in self.contracts.values()
                if c.contract_id not in amendment_ids and c.entity_ids == a.entity_ids
                and not (c.signature_date and a.signature_date and c.signature_date > a.signature_date)
            ]
            cited = set(dates_in_text(a.content))
            targets = [c for c in candidates if c.signature_date in cited] or (candidates if len(candidates) == 1 else [])
            if not targets:
                a.warnings.append("avenant non rattaché : contrat modifié non identifié")
                continue

            term_articles = [ch for ch in self.contract_chunks(a.contract_id) if DURATION_HEADING.search(plain(ch.heading))]
            term_dates = [d for ch in term_articles for d in dates_in_text(ch.text)]
            new_end = (term_dates[-1] if term_dates else a.end_date) if term_articles else None
            if term_dates and a.end_date and a.end_date != new_end:
                a.warnings.append(f"terme cité dans l'avenant ({new_end}) différent de sa date de fin ({a.end_date})")
            for c in targets:
                a.amends.append(c.contract_id)
                c.amended_by.append(a.contract_id)
                if new_end and new_end != c.end_date:
                    c.warnings.append(
                        f"terme modifié par l'avenant {a.contract_id} : {c.end_date or 'non renseigné'} → {new_end}"
                    )
                    c.end_date = new_end

    def _contextualize(self, chunk: Chunk) -> str:
        c = self.contracts[chunk.contract_id]
        parties = " ".join(p.raw for p in c.parties)
        return f"{c.title} {parties} {c.contract_type}\n{chunk.heading}\n{chunk.text}"

    @classmethod
    def from_json(cls, path: Path = DATA_PATH) -> "DataRoomIndex":
        return cls(load_contracts(path))


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_PATH
    index = DataRoomIndex.from_json(path)
    print(f"{len(index.contracts)} contrats, {len(index.chunks)} articles, {len(index.bm25.idf)} termes indexés")
    for cid, idxs in index.chunks_by_contract.items():
        print(f"  {cid} : " + " | ".join(index.chunks[i].heading for i in idxs))
