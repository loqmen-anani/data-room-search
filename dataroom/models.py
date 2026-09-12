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
    end_date: date | None  # date de fin en vigueur : tient compte des avenants qui reportent le terme
    initial_end_date: date | None  # date de fin des métadonnées, avant avenants
    governing_law: str | None
    content: str
    warnings: list[str]
    amends: list[str] = []  # pour un avenant : les contrats qu'il modifie
    amended_by: list[str] = []  # les avenants qui modifient ce contrat

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
    Avec `query`, classe les contrats par pertinence de leurs articles.
    Réponse par pages : `limit` contrats à partir de `offset` ; `next_offset` non nul = il en reste.
    Chaque résultat contient les articles pertinents à citer dans la réponse.
    Les avenants sont rattachés à leur contrat : la date de fin tient compte des reports de terme.
    """

    query: str | None = Field(
        None,
        description="Texte libre recherché dans les articles, ex. « résiliation anticipée », "
                    "« exclusivité territoriale ». Laisser vide pour une question purement sur les métadonnées.",
    )
    filters: Filters = Field(default_factory=Filters)
    limit: int = Field(20, ge=1, le=100, description="Nombre max de contrats renvoyés (page).")
    offset: int = Field(0, ge=0, description="Pour la suite : le `next_offset` de la réponse précédente.")


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
    amends: list[str] | None = None
    amended_by: list[str] | None = None
    warnings: list[str] | None = None  # SIREN invalide, date illisible, terme modifié par un avenant…
    matched_filters: list[str]
    relevant_articles: list[ArticleHit]
    score: float | None


class SearchResponse(BaseModel):
    total_candidates: int  # contrats passant les filtres, avant classement par la query
    total_results: int  # résultats avant pagination (avec query : contrats dont un article au moins correspond)
    next_offset: int | None  # offset de la page suivante ; absent (None) quand tout est renvoyé
    excluded_unknown: list[str]  # ids écartés parce qu'un champ filtré est vide : à signaler à l'avocat
    # Contrats qui passeraient le filtre de date sans l'avenant qui a modifié leur terme : id -> explication
    excluded_by_amendment: dict[str, str]
    results: list[ContractHit]


# --- Doublons -----------------------------------------------------------------

class FindDuplicates(BaseModel):
    """Repère les doublons probables : contrats aux mêmes parties qui décrivent le même acte (fichier téléversé deux
    fois, version signée et non signée, traduction de courtoisie). Chaque paire est renvoyée avec ses raisons ; c'est à
    l'agent de conclure, en vérifiant au besoin avec get_contract."""

    entity_ids: list[str] | None = Field(
        None, description="Limiter aux contrats impliquant TOUTES ces entités. Vide = toute la data room.",
    )


class DuplicatePair(BaseModel):
    contract_ids: list[str]
    titles: list[str]
    parties: list[str]
    reasons: list[str]  # « même type (…) », « même date de signature (…) », « texte identique à 98 % »…
    text_similarity: float  # Jaccard sur les mots des deux textes : 1 = même texte


class DuplicatesResponse(BaseModel):
    contracts_compared: int
    pairs: list[DuplicatePair]  # les plus ressemblantes d'abord
