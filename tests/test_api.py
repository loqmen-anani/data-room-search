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


def test_errors(client):
    assert client.post("/tools/get_contract", json={"contract_id": "c99"}).status_code == 404
    unknown = client.post("/tools/search_data_room", json={"filters": {"entity_ids": ["brenaliss"]}})
    assert unknown.status_code == 422 and "brenaliss" in unknown.json()["detail"]
    assert client.post("/tools/search_data_room", json={"filters": {"end_date": {"before": "fin 2026"}}}).status_code == 422
