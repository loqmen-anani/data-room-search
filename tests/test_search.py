import pytest

from dataroom.models import SearchRequest
from dataroom.search import search


def ids(resp):
    return [r.contract_id for r in resp.results]


def headings(resp, contract_id):
    hit = next(r for r in resp.results if r.contract_id == contract_id)
    return [a.heading for a in hit.relevant_articles]


# --- Questions types d'une due diligence (jeu fictif) ------------------------------

def test_entity_contracts_ending_before_end_2026(index):
    resp = search(index, SearchRequest.model_validate(
        {"filters": {"entity_ids": ["groupe_brenalis"], "end_date": {"before": "2026-12-31"}}}))
    assert ids(resp) == ["c04"]
    assert "c12" not in ids(resp)  # Brénalys Advisory ≠ Groupe Brenalis
    assert resp.excluded_unknown == ["c08", "c17"]  # cession de parts et CDI : pas de date de fin
    assert resp.excluded_by_amendment == {"c09": "fin 2026-06-30 → 2028-06-30 (avenant c18)"}
    assert headings(resp, "c04") == ["ARTICLE 2 — DURÉE"]


def test_amended_term_is_cited(index):
    resp = search(index, SearchRequest.model_validate(
        {"filters": {"entity_ids": ["groupe_brenalis"], "end_date": {"before": "2028-12-31"}}}))
    c09 = next(r for r in resp.results if r.contract_id == "c09")
    assert c09.end_date.isoformat() == "2028-06-30" and c09.amended_by == ["c18"]
    assert [a.chunk_id for a in c09.relevant_articles] == ["c09-3", "c18-2"]  # DURÉE du contrat, REPORT DU TERME de l'avenant


def test_empty_filters_are_ignored(index):
    resp = search(index, SearchRequest.model_validate({"filters": {"end_date": {}, "governing_law": {"not_in": []}}}))
    assert len(resp.results) == 20
    assert all(r.relevant_articles == [] for r in resp.results)


def test_foreign_governing_law(index):
    resp = search(index, SearchRequest.model_validate(
        {"filters": {"governing_law": {"not_in": ["droit français"]}}}))
    assert ids(resp) == ["c05", "c16", "c20"]
    assert resp.excluded_unknown == ["c10"]  # loi applicable non renseignée
    assert headings(resp, "c05") == ["ARTICLE 8 — GOVERNING LAW"]


def test_unknown_filter_value_is_an_error(index):
    with pytest.raises(ValueError, match="brenaliss"):
        search(index, SearchRequest.model_validate({"filters": {"entity_ids": ["brenaliss"]}}))


# --- Recherche plein texte ----------------------------------------------------

def test_query_returns_relevant_article(index):
    resp = search(index, SearchRequest(query="exclusivité territoriale"))
    assert ids(resp)[0] == "c03"
    assert headings(resp, "c03")[0] == "ARTICLE 4 — EXCLUSIVITÉ"


def test_query_combined_with_filters(index):
    resp = search(index, SearchRequest.model_validate(
        {"query": "loyer révisé indice", "filters": {"contract_types": ["bail commercial"]}}))
    assert resp.total_candidates == 3
    assert ids(resp)[0] == "c02"
    assert headings(resp, "c02")[0] == "ARTICLE 3 — LOYER ET RÉVISION"


def test_query_finds_what_metadata_misses(index):
    resp = search(index, SearchRequest(query="franchise"))
    assert ids(resp) == ["c13"]  # typé « contrat de licence » dans les métadonnées


def test_query_without_match_returns_nothing(index):
    resp = search(index, SearchRequest(query="blockchain cryptomonnaie"))
    assert resp.results == []


def test_query_with_only_stopwords_is_an_error(index):
    with pytest.raises(ValueError, match="mots vides"):
        search(index, SearchRequest(query="le la de"))


def test_pagination_with_query(index):
    first = search(index, SearchRequest(query="durée", limit=3))
    assert len(first.results) == 3 and first.next_offset == 3 and first.total_results > 3
    assert [r.score for r in first.results] == sorted((r.score for r in first.results), reverse=True)
    second = search(index, SearchRequest(query="durée", limit=3, offset=3))
    assert not {r.contract_id for r in first.results} & {r.contract_id for r in second.results}


def test_pagination_without_query_keeps_every_contract(index):
    page = search(index, SearchRequest(limit=15))
    assert [r.contract_id for r in page.results] == [f"c{i:02d}" for i in range(1, 16)]
    assert (page.total_results, page.next_offset) == (20, 15)
    rest = search(index, SearchRequest(limit=15, offset=15))
    assert [r.contract_id for r in rest.results] == ["c16", "c17", "c18", "c19", "c20"] and rest.next_offset is None
