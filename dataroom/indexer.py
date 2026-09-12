"""Indexation de la data room : découpage par article + index BM25.

Usage : python -m dataroom.indexer [chemin/vers/data_room.json]
"""

import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from dataroom.config import DATA_PATH
from dataroom.loader import load_contracts
from dataroom.models import Chunk, Contract

# "ARTICLE 6 — DURÉE" (tiret cadratin, demi-cadratin ou simple)
ARTICLE_RE = re.compile(r"^ARTICLE\s+\d+\s*[—–-].*$", re.MULTILINE)

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

def tokenize(text: str) -> list[str]:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
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
        # Enrichissement contextuel : titre et parties indexés avec chaque article.
        self.bm25 = BM25([tokenize(self._contextualize(ch)) for ch in self.chunks])
        # Valeurs présentes dans la data room : proposées au LLM dans le schéma du tool, seules acceptées en filtre.
        self.entities = {e for c in contracts for e in c.entity_ids}
        self.contract_types = {c.contract_type for c in contracts}
        self.laws = {c.governing_law for c in contracts if c.governing_law}

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
