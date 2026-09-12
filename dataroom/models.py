"""Schémas : data room, entrée et sortie du tool.

Les valeurs possibles des filtres (entités, types de contrat, lois) ne sont pas codées ici : elles sont tirées de la
data room chargée, injectées dans le schéma du tool (`dataroom.tools`) et vérifiées à la recherche (`dataroom.search`).
"""

from datetime import date

from pydantic import BaseModel, Field


# --- Data room ----------------------------------------------------------------

class Party(BaseModel):
    entity_id: str
    raw: str
    siren: str | None


class Contract(BaseModel):
    contract_id: str
    filename: str
    title: str
    parties: list[Party]
    contract_type: str
    signature_date: date | None
    end_date: date | None
    governing_law: str | None
    content: str
    warnings: list[str]

    @property
    def entity_ids(self) -> set[str]:
        return {p.entity_id for p in self.parties}


class Chunk(BaseModel):
    """Un article d'un contrat : l'unité indexée et renvoyée à l'agent."""

    chunk_id: str
    contract_id: str
    heading: str  # "ARTICLE 6 — DURÉE", ou "PRÉAMBULE" pour le texte avant le premier article
    text: str


# --- Entrée du tool -----------------------------------------------------------

class DateRange(BaseModel):
    after: date | None = Field(None, description="À cette date ou après (YYYY-MM-DD).")
    before: date | None = Field(None, description="À cette date ou avant (YYYY-MM-DD).")


class LawFilter(BaseModel):
    in_: list[str] | None = Field(None, alias="in", description="Régi par l'un de ces droits.")
    not_in: list[str] | None = Field(
        None, description="Régi par aucun de ces droits. « Droit étranger » = not_in: [\"droit français\"].",
    )


class Filters(BaseModel):
    entity_ids: list[str] | None = Field(
        None,
        description="Contrats impliquant TOUTES ces entités. Des noms proches peuvent désigner des entités "
                    "différentes : utiliser l'identifiant exact.",
    )
    contract_types: list[str] | None = Field(None, description="Au moins un de ces types.")
    governing_law: LawFilter | None = None
    signature_date: DateRange | None = None
    end_date: DateRange | None = None


class SearchRequest(BaseModel):
    """Recherche dans la data room : filtres sur les métadonnées et/ou recherche plein texte dans les articles.

    Sans `query`, renvoie TOUS les contrats qui passent les filtres (réponse exhaustive).
    Avec `query`, classe les contrats par pertinence de leurs articles et renvoie les `top_k` premiers.
    Chaque résultat contient les articles pertinents à citer dans la réponse.
    """

    query: str | None = Field(
        None,
        description="Texte libre recherché dans les articles, ex. « résiliation anticipée », "
                    "« exclusivité territoriale ». Laisser vide pour une question purement sur les métadonnées.",
    )
    filters: Filters = Field(default_factory=Filters)
    top_k: int = Field(10, ge=1, le=100, description="Nombre max de contrats renvoyés quand `query` est fournie.")


# --- Sortie du tool -----------------------------------------------------------

class ArticleHit(BaseModel):
    chunk_id: str
    heading: str
    excerpt: str
    score: float | None  # score BM25, None quand l'article est remonté par un filtre


class ContractHit(BaseModel):
    contract_id: str
    filename: str
    title: str
    parties: list[Party]
    contract_type: str
    signature_date: date | None
    end_date: date | None
    governing_law: str | None
    matched_filters: list[str]
    relevant_articles: list[ArticleHit]
    score: float | None


class SearchResponse(BaseModel):
    total_candidates: int  # contrats passant les filtres, avant classement par la query
    excluded_unknown: list[str]  # ids écartés parce qu'un champ filtré est vide : à signaler à l'avocat
    results: list[ContractHit]
