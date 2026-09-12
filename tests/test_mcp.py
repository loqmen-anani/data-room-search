"""Serveur MCP : client officiel (in-process et stdio), transport HTTP (JSON-RPC brut, hôte, jeton, tunnel)."""

import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.shared.exceptions import MCPError
from mcp_types.jsonrpc import INVALID_PARAMS
from starlette.testclient import TestClient

from dataroom import mcp_server
from dataroom.mcp_server import http_app, server

FOREIGN_LAW = {"filters": {"governing_law": {"not_in": ["droit français"]}}}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def rpc(method, params=None):
    return {"jsonrpc": "2.0", "id": 1, "method": method, **({"params": params} if params else {})}


# --- Client MCP officiel -------------------------------------------------------

@pytest.mark.anyio
async def test_list_and_call_tools():
    async with Client(server) as client:
        assert [t.name for t in (await client.list_tools()).tools] == ["search_data_room", "get_contract", "find_duplicates"]
        result = await client.call_tool("search_data_room", FOREIGN_LAW)
    assert not result.is_error
    assert [r["contract_id"] for r in result.structured_content["results"]] == ["c05", "c16", "c20"]
    assert result.structured_content["excluded_unknown"] == ["c10"]


@pytest.mark.anyio
async def test_tool_errors_are_returned_to_the_model():
    async with Client(server) as client:
        bad_date = await client.call_tool("search_data_room", {"filters": {"end_date": {"before": "fin 2026"}}})
        unknown_entity = await client.call_tool("search_data_room", {"filters": {"entity_ids": ["brenaliss"]}})
        unknown_contract = await client.call_tool("get_contract", {"contract_id": "c99"})
    assert bad_date.is_error and "ValidationError" in bad_date.content[0].text
    assert unknown_entity.is_error and "brenaliss" in unknown_entity.content[0].text
    assert unknown_contract.is_error and "c99" in unknown_contract.content[0].text


@pytest.mark.anyio
async def test_unknown_tool_is_a_protocol_error():
    async with Client(server) as client:
        with pytest.raises(MCPError) as exc:
            await client.call_tool("nope", {})
    assert exc.value.code == INVALID_PARAMS


@pytest.mark.anyio
async def test_stdio_transport():
    # Le sous-processus reçoit l'environnement, donc DATAROOM_DATA (jeu fictif) fixé par conftest.py.
    params = StdioServerParameters(command=sys.executable, args=["-m", "dataroom.mcp_server"], env=dict(os.environ))
    async with Client(params) as client:
        result = await client.call_tool("get_contract", {"contract_id": "c03", "chunk_ids": ["c03-3"]})
    assert result.structured_content["articles"][0]["heading"] == "ARTICLE 4 — EXCLUSIVITÉ"


# --- Transport HTTP --------------------------------------------------------------

def test_http_raw_json_rpc():
    with TestClient(http_app(), base_url="http://127.0.0.1:8002") as client:
        resp = client.post("/mcp", json=rpc("tools/call", {"name": "search_data_room", "arguments": FOREIGN_LAW}),
                           headers=HEADERS)
    assert resp.status_code == 200
    assert [r["contract_id"] for r in resp.json()["result"]["structuredContent"]["results"]] == ["c05", "c16", "c20"]


def test_http_rejects_foreign_host_on_localhost():
    with TestClient(http_app(), base_url="http://127.0.0.1:8002") as client:
        assert client.post("/mcp", json=rpc("tools/list"), headers={**HEADERS, "Host": "evil.example"}).status_code == 421


def test_http_bearer_token():
    with TestClient(http_app("0.0.0.0", 8002, token="s3cret"), base_url="http://127.0.0.1:8002") as client:
        assert client.post("/mcp", json=rpc("tools/list"), headers=HEADERS).status_code == 401
        wrong = {**HEADERS, "Authorization": "Bearer nope"}
        assert client.post("/mcp", json=rpc("tools/list"), headers=wrong).status_code == 401
        right = {**HEADERS, "Authorization": "Bearer s3cret"}
        assert client.post("/mcp", json=rpc("tools/list"), headers=right).status_code == 200


def test_refuses_network_exposure_without_token(monkeypatch):
    monkeypatch.setattr(mcp_server, "MCP_TOKEN", None)
    monkeypatch.setattr(sys, "argv", ["mcp_server", "--http", "--host", "0.0.0.0"])
    with pytest.raises(SystemExit, match="jeton"):
        mcp_server.main()


# --- Tunnel HTTPS (connecteur personnalisé de Claude) ------------------------------

def test_http_tunnel_host_and_secret_path():
    app = http_app(path="/mcp/s3cret", allowed_hosts=["demo.ngrok-free.app"])
    with TestClient(app, base_url="https://demo.ngrok-free.app") as client:
        assert client.post("/mcp/s3cret", json=rpc("tools/list"), headers=HEADERS).status_code == 200
        assert client.post("/mcp", json=rpc("tools/list"), headers=HEADERS).status_code == 404
        evil = {**HEADERS, "Host": "evil.example"}
        assert client.post("/mcp/s3cret", json=rpc("tools/list"), headers=evil).status_code == 421


def test_refuses_tunnel_without_secret(monkeypatch):
    monkeypatch.setattr(mcp_server, "MCP_TOKEN", None)
    monkeypatch.setattr(sys, "argv", ["mcp_server", "--http", "--allow-host", "demo.ngrok-free.app"])
    with pytest.raises(SystemExit, match="chemin secret"):
        mcp_server.main()
