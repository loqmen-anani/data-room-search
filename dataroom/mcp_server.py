"""Serveur MCP : expose les tools de la data room à n'importe quel client MCP (Claude Desktop, Claude Code, Cursor…).

Même contrat que l'API REST et l'agent Ollama : `tool_definitions()` et `run_tool()` de `dataroom.tools`.

Local (stdio)   : dataroom-mcp        (= python -m dataroom.mcp_server)
Réseau (HTTP)   : dataroom-mcp --http [--host 0.0.0.0] [--port 8002]   → http://<hôte>:<port>/mcp
                  Hors localhost, un jeton est obligatoire : DATAROOM_MCP_TOKEN=<secret>,
                  à envoyer dans le header « Authorization: Bearer <secret> ».
Tunnel HTTPS    : dataroom-mcp --http --allow-host <domaine du tunnel> --path /mcp/<secret>
                  Pour le connecteur personnalisé de Claude, qui ne prend qu'une URL : le chemin secret sert de clé
                  (voir scripts/mcp_tunnel.sh).
"""

import argparse
import hmac
import json
import sys

import anyio
import uvicorn
from mcp import types
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from mcp_types.jsonrpc import INVALID_PARAMS
from pydantic import ValidationError
from starlette.applications import Starlette

from dataroom.config import MCP_TOKEN
from dataroom.tools import TOOLS, run_tool, tool_definitions

LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
DEFAULT_PATH = "/mcp"

INSTRUCTIONS = (
    "Data room de contrats. search_data_room : sans `query`, renvoie TOUS les contrats qui passent les filtres "
    "(réponse exhaustive) ; avec `query`, classe les articles par pertinence. Dates au format YYYY-MM-DD. "
    "Les contrats listés dans `excluded_unknown` ont un champ filtré vide, ceux de `excluded_by_amendment` un terme "
    "modifié par un avenant : signalez-les. "
    "get_contract renvoie le texte d'un contrat par article, pour citer la source."
)


async def list_tools(_ctx, _params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
    return types.ListToolsResult(tools=[
        types.Tool(name=t["name"], description=t["description"], input_schema=t["input_schema"])
        for t in tool_definitions()
    ])


async def call_tool(_ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    if params.name not in TOOLS:
        raise MCPError(INVALID_PARAMS, f"tool inconnu : {params.name}")  # erreur de protocole (spec MCP)
    try:
        result = run_tool(params.name, params.arguments or {})
    except (ValidationError, KeyError, ValueError) as e:
        # Erreur du tool : renvoyée dans le résultat (is_error) pour que le LLM client corrige son appel.
        return types.CallToolResult(content=[types.TextContent(text=f"{type(e).__name__}: {e}")], is_error=True)
    return types.CallToolResult(content=[types.TextContent(text=result)], structured_content=json.loads(result))


server = Server(
    "data-room-search",
    version="0.2.0",
    instructions=INSTRUCTIONS,
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


class StaticTokenVerifier:
    """Vérifie le jeton Bearer partagé (DATAROOM_MCP_TOKEN)."""

    def __init__(self, token: str):
        self._token = token.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token.encode(), self._token):
            return AccessToken(token=token, client_id="dataroom-client", scopes=[])
        return None


def http_app(
    host: str = "127.0.0.1",
    port: int = 8002,
    token: str | None = None,
    path: str = DEFAULT_PATH,
    allowed_hosts: list[str] | tuple[str, ...] = (),
) -> Starlette:
    """App Streamable HTTP, sans état et en JSON : un simple POST suffit, pas de session à gérer.

    `allowed_hosts` : domaines publics acceptés en plus de localhost (ex. un tunnel HTTPS). La protection contre
    le DNS rebinding reste active pour tous les autres."""
    auth = {}
    if token:
        auth = {
            # Jeton statique : pas de serveur OAuth ni de métadonnées de ressource protégée.
            "auth": AuthSettings(issuer_url=f"http://{host}:{port}", resource_server_url=None, required_scopes=[]),
            "token_verifier": StaticTokenVerifier(token),
        }
    security = None  # défaut du SDK : seulement localhost quand `host` est local
    if allowed_hosts:
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *allowed_hosts],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
                             *(f"https://{h}" for h in allowed_hosts)],
        )
    return server.streamable_http_app(json_response=True, stateless_http=True, host=host,
                                      streamable_http_path=path, transport_security=security, **auth)


async def serve_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--http", action="store_true", help="Streamable HTTP au lieu de stdio")
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 pour accepter les connexions du réseau")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--path", default=DEFAULT_PATH, help="chemin de l'endpoint ; derrière un tunnel, un chemin secret")
    parser.add_argument("--allow-host", action="append", default=[], metavar="DOMAINE",
                        help="domaine public accepté en plus de localhost (ex. celui d'un tunnel HTTPS)")
    args = parser.parse_args()

    if not args.http:
        anyio.run(serve_stdio)
        return
    if args.host not in LOCAL_HOSTS and not MCP_TOKEN:
        sys.exit("Exposer la data room hors de localhost exige un jeton : DATAROOM_MCP_TOKEN=<secret>.")
    if args.allow_host and not MCP_TOKEN and args.path == DEFAULT_PATH:
        sys.exit("Derrière un tunnel, il faut une clé : un chemin secret (--path /mcp/<secret>) ou DATAROOM_MCP_TOKEN.")
    uvicorn.run(http_app(args.host, args.port, MCP_TOKEN, args.path, args.allow_host), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
