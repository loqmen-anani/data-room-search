"""Configuration, surchargeable par variables d'environnement."""

import os
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Data room à indexer : DATAROOM_DATA, sinon le jeu fictif publiable. Des données réelles se placent dans private/,
# jamais versionné : DATAROOM_DATA=private/<fichier>.json.
EXAMPLE_DATA = ROOT / "data" / "exemple_data_room.json"
DATA_PATH = Path(os.environ.get("DATAROOM_DATA") or EXAMPLE_DATA)

# LLM de l'agent (Ollama)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("DATAROOM_MODEL", "huihui_ai/qwen3.5-abliterated:27b")

# Serveur MCP en HTTP : jeton Bearer, obligatoire hors localhost
MCP_TOKEN = os.environ.get("DATAROOM_MCP_TOKEN")
