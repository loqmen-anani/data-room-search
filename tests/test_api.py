import pytest
from fastapi.testclient import TestClient

from dataroom.api import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_search_endpoint(client):
    resp = client.post("/tools/search_data_room", json={"filters": {"governing_law": {"in": ["droit suisse"]}}})
    assert resp.status_code == 200
    assert [r["contract_id"] for r in resp.json()["results"]] == ["c16"]
    assert "warnings" not in resp.json()["results"][0]  # champs à None omis de la réponse

    resp = client.post("/tools/search_data_room",
                       json={"filters": {"entity_ids": ["groupe_brenalis"], "end_date": {"before": "2026-12-31"}}})
    assert list(resp.json()["excluded_by_amendment"]) == ["c09"]


def test_find_duplicates_endpoint(client):
    resp = client.post("/tools/find_duplicates", json={"entity_ids": ["kessler_aubry_avocats"]})
    assert resp.status_code == 200
    assert [p["contract_ids"] for p in resp.json()["pairs"]] == [["c11", "c19"]]


def test_errors(client):
    assert client.post("/tools/get_contract", json={"contract_id": "c99"}).status_code == 404
    unknown = client.post("/tools/search_data_room", json={"filters": {"entity_ids": ["brenaliss"]}})
    assert unknown.status_code == 422 and "brenaliss" in unknown.json()["detail"]
    assert client.post("/tools/search_data_room", json={"filters": {"end_date": {"before": "fin 2026"}}}).status_code == 422
