"""Boucle d'agent testée avec un faux LLM : pas besoin d'Ollama, résultat déterministe."""

import json

from dataroom import agent
from dataroom.tools import tool_definitions


def fake_llm(replies):
    """Remplace `agent.chat` : renvoie les messages scriptés dans l'ordre et garde les conversations reçues."""
    seen = []

    def chat(model, messages, tools, think):
        seen.append(list(messages))
        return replies[len(seen) - 1]

    return chat, seen


def tool_call(name, arguments):
    call = {"id": "call_1", "function": {"name": name, "arguments": arguments}}
    return {"role": "assistant", "content": "", "tool_calls": [call]}


def test_loop_runs_tool_then_answers(monkeypatch):
    chat, seen = fake_llm([
        tool_call("search_data_room", {"filters": {"governing_law": {"not_in": ["droit français"]}}}),
        {"role": "assistant", "content": "c05, c16 et c20."},
    ])
    monkeypatch.setattr(agent, "chat", chat)

    out = agent.run_agent("Lesquels sont régis par un droit étranger ?")

    assert out.answer == "c05, c16 et c20."
    assert [c.name for c in out.tool_calls] == ["search_data_room"]
    tool_msg = seen[1][-1]  # le résultat du tool est renvoyé au LLM au 2e tour
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_1"
    assert [r["contract_id"] for r in json.loads(tool_msg["content"])["results"]] == ["c05", "c16", "c20"]


def test_invalid_arguments_are_returned_to_the_model(monkeypatch):
    chat, seen = fake_llm([
        tool_call("search_data_room", {"filters": {"end_date": {"before": "fin 2026"}}}),
        {"role": "assistant", "content": "Je corrige la date."},
    ])
    monkeypatch.setattr(agent, "chat", chat)

    out = agent.run_agent("…")

    assert "ValidationError" in json.loads(out.tool_calls[0].result)["error"]


def test_summarize_result_mentions_amendments():
    result = json.dumps({"results": [{"contract_id": "c04"}], "excluded_unknown": ["c08"],
                         "excluded_by_amendment": {"c09": "fin 2026-06-30 → 2028-06-30 (avenant c18)"}})
    assert agent.summarize_result(result) == "1 résultat(s) : ['c04'], inconnus : ['c08'], écartés par un avenant : ['c09']"
    assert agent.summarize_result(json.dumps({"error": "x"})) == "erreur : x"
    pairs = json.dumps({"contracts_compared": 20, "pairs": [{"contract_ids": ["c11", "c19"]}]})
    assert agent.summarize_result(pairs) == "1 paire(s) de doublons : [['c11', 'c19']]"


def test_ollama_tools_format():
    tools = agent.ollama_tools()
    assert [t["function"]["name"] for t in tools] == [t["name"] for t in tool_definitions()]
    assert all(t["type"] == "function" and t["function"]["parameters"]["type"] == "object" for t in tools)
