"""Tools exposés à l'agent : définitions au format de l'API Claude + exécution."""

from functools import cache

from pydantic import BaseModel, Field

from dataroom.indexer import DataRoomIndex
from dataroom.models import Chunk, SearchRequest
from dataroom.search import search


class GetContract(BaseModel):
    """Renvoie le texte d'un contrat, découpé par article, pour vérifier ou citer une clause précise."""

    contract_id: str = Field(description="Identifiant renvoyé par search_data_room, ex. « c07 ».")
    chunk_ids: list[str] | None = Field(None, description="Limiter à ces articles (ex. « c07-2 »). Vide = tout le contrat.")


class ContractText(BaseModel):
    contract_id: str
    title: str
    articles: list[Chunk]


@cache
def get_index() -> DataRoomIndex:
    return DataRoomIndex.from_json()


def get_contract(params: GetContract) -> ContractText:
    index = get_index()
    contract = index.contracts.get(params.contract_id)
    if contract is None:
        raise KeyError(f"contrat inconnu : {params.contract_id}")
    chunks = [index.chunks[i] for i in index.chunks_by_contract.get(contract.contract_id, [])]
    if params.chunk_ids:
        chunks = [ch for ch in chunks if ch.chunk_id in params.chunk_ids]
    return ContractText(contract_id=contract.contract_id, title=contract.title, articles=chunks)


TOOLS = {
    "search_data_room": (SearchRequest, lambda req: search(get_index(), req)),
    "get_contract": (GetContract, get_contract),
}


def _simplify(node, defs: dict):
    """Aplatit le schéma Pydantic : $ref inlinés, `anyOf [X, null]` -> X, titres et `default: null` retirés.
    Moins de tokens et plus facile à suivre pour un petit modèle."""
    if isinstance(node, list):
        return [_simplify(v, defs) for v in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        extra = {k: v for k, v in node.items() if k != "$ref"}
        return _simplify({**defs[node["$ref"].split("/")[-1]], **extra}, defs)
    if "anyOf" in node:
        variants = [v for v in node["anyOf"] if v != {"type": "null"}]
        if len(variants) == 1:
            return _simplify({**{k: v for k, v in node.items() if k != "anyOf"}, **variants[0]}, defs)
    return {
        k: _simplify(v, defs) for k, v in node.items()
        if k != "$defs" and not (k == "title" and isinstance(v, str)) and not (k == "default" and v is None)
    }


def _inject_enums(schema: dict) -> dict:
    """Ajoute au schéma de search_data_room les valeurs présentes dans la data room (entités, types, lois)."""
    index = get_index()
    filters = schema["properties"]["filters"]["properties"]
    filters["entity_ids"]["items"]["enum"] = sorted(index.entities)
    filters["contract_types"]["items"]["enum"] = sorted(index.contract_types)
    for key in ("in", "not_in"):
        filters["governing_law"]["properties"][key]["items"]["enum"] = sorted(index.laws)
    return schema


def tool_definitions() -> list[dict]:
    """Définitions neutres (format de l'API Claude) ; `dataroom.agent` les convertit pour Ollama."""
    definitions = []
    for name, (model, _) in TOOLS.items():
        schema = model.model_json_schema()
        schema = _simplify(schema, schema.get("$defs", {}))
        schema.pop("description", None)  # doublon de la description du tool
        if model is SearchRequest:
            schema = _inject_enums(schema)
        definitions.append({"name": name, "description": model.__doc__.strip(), "input_schema": schema})
    return definitions


def run_tool(name: str, tool_input: dict) -> str:
    model, fn = TOOLS[name]
    return fn(model.model_validate(tool_input)).model_dump_json(exclude_none=True)
