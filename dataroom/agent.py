"""Agent de bout en bout : un LLM local (Ollama) répond aux questions en appelant les tools de la data room.

Usage : python -m dataroom.agent "Lesquels sont régis par un droit étranger ?" [--model M] [--think]
"""

import argparse
import json
import time
from datetime import date

import httpx
from pydantic import BaseModel, ValidationError

from dataroom.config import DEFAULT_MODEL, OLLAMA_URL
from dataroom.tools import run_tool, tool_definitions

MAX_STEPS = 6

SYSTEM_PROMPT = """Tu es l'assistant d'un avocat qui analyse une data room de contrats. Date du jour : {today}.

Règles :
- Réponds uniquement à partir des résultats des tools. N'invente jamais un contrat, une date ou une clause.
- Convertis toute date relative (« fin 2026 », « l'an prochain ») en date absolue YYYY-MM-DD avant d'appeler un tool.
- Pour une question de liste (« quels contrats », « lesquels »), utilise les filtres sans query : la réponse est exhaustive.
- Pour une question sur le contenu des clauses, utilise `query`, éventuellement avec des filtres.
- Cite chaque contrat par son titre et son identifiant (ex. c07), avec l'article qui justifie la réponse.
- Si `excluded_unknown` n'est pas vide, signale ces contrats : leur situation ne peut pas être déterminée.
- Si `excluded_by_amendment` n'est pas vide, signale ces contrats : un avenant a modifié leur terme.
- Réponds en français, de façon concise."""


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result: str


class AgentAnswer(BaseModel):
    answer: str
    tool_calls: list[ToolCall]
    model: str
    duration_s: float


def ollama_tools() -> list[dict]:
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in tool_definitions()
    ]


def chat(model: str, messages: list[dict], tools: list[dict], think: bool) -> dict:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": model, "messages": messages, "tools": tools, "stream": False, "think": think,
              "options": {"temperature": 0}},
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()["message"]


def call_tool(name: str, arguments: dict | str) -> str:
    """Exécute le tool ; une erreur est renvoyée au modèle (et non levée) pour qu'il corrige son appel."""
    try:
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return run_tool(name, arguments)
    except (ValidationError, KeyError, ValueError) as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)


def run_agent(question: str, model: str = DEFAULT_MODEL, think: bool = False, verbose: bool = False) -> AgentAnswer:
    start = time.monotonic()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().isoformat())},
        {"role": "user", "content": question},
    ]
    tools = ollama_tools()
    calls: list[ToolCall] = []
    for _ in range(MAX_STEPS):
        msg = chat(model, messages, tools, think)
        messages.append(msg)
        if not msg.get("tool_calls"):
            return AgentAnswer(answer=msg.get("content", ""), tool_calls=calls, model=model,
                               duration_s=round(time.monotonic() - start, 1))
        for tc in msg["tool_calls"]:
            name, args = tc["function"]["name"], tc["function"]["arguments"]
            result = call_tool(name, args)
            calls.append(ToolCall(name=name, arguments=args if isinstance(args, dict) else {"raw": args}, result=result))
            if verbose:
                print(f"→ {name}({json.dumps(args, ensure_ascii=False)})\n  {summarize_result(result)}")
            messages.append({"role": "tool", "tool_name": name, "tool_call_id": tc.get("id"), "content": result})
    return AgentAnswer(answer="Nombre maximal d'étapes atteint sans réponse finale.", tool_calls=calls, model=model,
                       duration_s=round(time.monotonic() - start, 1))


def summarize_result(result: str) -> str:
    """Résumé d'une ligne du résultat d'un tool (pour les traces)."""
    data = json.loads(result)
    if "error" in data:
        return f"erreur : {data['error'][:200]}"
    if "results" in data:
        summary = f"{len(data['results'])} résultat(s) : {[r['contract_id'] for r in data['results']]}"
        summary += f", inconnus : {data['excluded_unknown']}"
        if data.get("excluded_by_amendment"):
            summary += f", écartés par un avenant : {list(data['excluded_by_amendment'])}"
        return summary
    return f"{data.get('contract_id')} : {len(data.get('articles', []))} article(s)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--think", action="store_true", help="active le raisonnement (modèles « thinking », plus lent)")
    args = parser.parse_args()
    out = run_agent(args.question, model=args.model, think=args.think, verbose=True)
    print(f"\n{out.answer}\n\n[{out.model} · {len(out.tool_calls)} appel(s) de tool · {out.duration_s} s]")
