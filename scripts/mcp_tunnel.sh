#!/usr/bin/env bash
# Expose le serveur MCP en HTTPS, pour le connecteur personnalisé de Claude (Desktop ou claude.ai).
# Tunnel : cloudflared s'il est installé (gratuit, sans compte : brew install cloudflared), sinon ngrok (compte vérifié).
# L'URL affichée contient un chemin secret : c'est la clé d'accès à la data room, ne la partage pas.
# Usage : bash scripts/mcp_tunnel.sh        (Ctrl+C arrête le tunnel et le serveur)
#         MCP_SECRET=<secret> bash scripts/mcp_tunnel.sh   pour garder le même chemin secret
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8002}"
SECRET="${MCP_SECRET:-$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(18))')}"
LOG=$(mktemp)
SERVER_PID=""

if command -v cloudflared >/dev/null; then
  TOOL=cloudflared
  cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" >"$LOG" 2>&1 &
elif command -v ngrok >/dev/null; then
  TOOL=ngrok
  ngrok http "$PORT" --log stdout --log-format json >"$LOG" 2>&1 &
else
  echo "Aucun outil de tunnel : brew install cloudflared" >&2
  exit 1
fi
TUNNEL_PID=$!
trap 'kill $TUNNEL_PID $SERVER_PID 2>/dev/null; rm -f "$LOG"' EXIT

tunnel_url() {
  if [ "$TOOL" = cloudflared ]; then
    grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | grep -v '://api\.' | head -1
  else
    grep -o '"url":"https://[^"]*"' "$LOG" | head -1 | cut -d'"' -f4
  fi
}

# Attend l'URL publique attribuée par le tunnel
URL=""
for _ in $(seq 1 60); do
  URL=$(tunnel_url || true)
  [ -n "$URL" ] && break
  kill -0 "$TUNNEL_PID" 2>/dev/null || { echo "$TOOL s'est arrêté :" >&2; cat "$LOG" >&2; exit 1; }
  sleep 0.5
done
[ -n "$URL" ] || { echo "Pas d'URL $TOOL après 30 s :" >&2; cat "$LOG" >&2; exit 1; }

# Le connecteur ne peut pas envoyer de jeton Bearer : la clé est le chemin secret.
env -u DATAROOM_MCP_TOKEN .venv/bin/dataroom-mcp --http --port "$PORT" --path "/mcp/$SECRET" --allow-host "${URL#https://}" &
SERVER_PID=$!
echo
echo "URL du connecteur MCP : $URL/mcp/$SECRET"
echo "(Ctrl+C pour tout arrêter)"
wait "$SERVER_PID"
