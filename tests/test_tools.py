import json

from dataroom.tools import run_tool, tool_definitions


def test_tool_definitions_are_flat_with_data_room_values():
    definitions = tool_definitions()
    assert [t["name"] for t in definitions] == ["search_data_room", "get_contract"]
    schemas = json.dumps([t["input_schema"] for t in definitions])
    assert "$ref" not in schemas and "anyOf" not in schemas
    filters = definitions[0]["input_schema"]["properties"]["filters"]["properties"]
    assert "groupe_brenalis" in filters["entity_ids"]["items"]["enum"]
    assert filters["governing_law"]["properties"]["not_in"]["items"]["enum"] == [
        "droit français", "droit new-yorkais", "droit suisse",
    ]


def test_run_tool_get_contract():
    out = json.loads(run_tool("get_contract", {"contract_id": "c18", "chunk_ids": ["c18-2"]}))
    assert out["articles"][0]["heading"] == "ARTICLE 2 — REPORT DU TERME"
