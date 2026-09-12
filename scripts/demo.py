"""Démo de bout en bout : pose des questions types à l'agent et écrit la trace en Markdown.

Usage : python scripts/demo.py [question ...] [--model M] [--out FICHIER]
Par défaut : les questions ci-dessous, sur la data room chargée (DATAROOM_DATA, sinon le jeu fictif).
Une démo sur d'autres données que le jeu fictif est écrite dans private/ (jamais versionné), pas dans docs/.
Ollama doit tourner ; compter ~1 min par question avec un 27B.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from dataroom.agent import run_agent, summarize_result
from dataroom.config import DATA_PATH, DEFAULT_MODEL, EXAMPLE_DATA, ROOT

QUESTIONS = [
    "Quels contrats avec le Groupe Brenalis expirent avant fin 2026 ?",
    "Lesquels sont régis par un droit étranger ?",
    "Y a-t-il des doublons ?",
    "Un changement de contrôle du Groupe Brenalis aurait-il des conséquences sur ses contrats ?",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("questions", nargs="*", help="questions à poser (défaut : questions types du jeu fictif)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, help="fichier de sortie (défaut : docs/demo.md sur le jeu fictif, private/demo.md sinon)")
    args = parser.parse_args()

    public = DATA_PATH.resolve() == EXAMPLE_DATA.resolve()
    out = args.out or (ROOT / "docs" / "demo.md" if public else ROOT / "private" / "demo.md")
    lines = [
        "# Démo de bout en bout",
        "",
        f"Générée le {datetime.now():%Y-%m-%d %H:%M} par `python scripts/demo.py`, data room `{DATA_PATH.name}`, "
        f"modèle `{args.model}` (Ollama).",
        "Pour chaque question : les appels de tools choisis par l'agent, puis sa réponse.",
        "",
    ]
    for question in args.questions or QUESTIONS:
        print(f"… {question}", flush=True)
        result = run_agent(question, model=args.model)
        lines += [f"## {question}", ""]
        for call in result.tool_calls:
            lines += [
                f"**Appel** `{call.name}` → {summarize_result(call.result)}",
                "```json",
                json.dumps(call.arguments, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        lines += ["**Réponse de l'agent**", ""]
        lines += [f"> {line}" if line else ">" for line in result.answer.strip().splitlines()]
        lines += ["", f"_{len(result.tool_calls)} appel(s) de tool · {result.duration_s} s_", ""]
        print(f"  {len(result.tool_calls)} appel(s), {result.duration_s} s", flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
