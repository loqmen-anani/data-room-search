#!/usr/bin/env bash
# Recherche seule (sans LLM) : envoie une query à search_data_room et affiche le JSON de sortie.
# Usage : bash scripts/run_query.sh ["texte de la requête"]    (port : PORT=8002 bash scripts/run_query.sh)
cd "$(dirname "$0")/.."
PORT="${PORT:-8001}"
QUERY="${1:-exclusivité territoriale}"

# Réutilise l'API si elle tourne déjà (ex. uvicorn --reload dans un autre terminal), sinon la démarre
if ! curl -sf -m 2 localhost:$PORT/tools >/dev/null; then
  .venv/bin/uvicorn dataroom.api:app --port $PORT >/dev/null 2>&1 &
  SERVER_PID=$!
  trap 'kill $SERVER_PID' EXIT
  until curl -sf -m 2 localhost:$PORT/tools >/dev/null; do
    kill -0 $SERVER_PID 2>/dev/null || { echo "uvicorn n'a pas démarré (port $PORT occupé ?)" >&2; exit 1; }
    sleep 0.2
  done
fi

curl -s -X POST localhost:$PORT/tools/search_data_room \
  -H 'Content-Type: application/json' \
  -d "$(.venv/bin/python -c 'import json,sys; print(json.dumps({"query": sys.argv[1]}))' "$QUERY")" \
  | .venv/bin/python -m json.tool --no-ensure-ascii
