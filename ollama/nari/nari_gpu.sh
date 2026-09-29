#!/usr/bin/env bash
# Nari Ollama on ComfyBox 5090 — status / unload / warm.
set -euo pipefail
cmd="${1:-status}"
HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
BASE="http://${HOST}"

unload_one() {
  local tag="$1"
  curl -sS -m 15 -X POST "$BASE/api/generate" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$tag\",\"keep_alive\":0,\"prompt\":\"\"}" >/dev/null || true
  echo "unload requested: $tag"
}

case "$cmd" in
  status)
    echo "=== ollama ps ==="
    ollama ps || true
    echo "=== nvidia ==="
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
    ;;
  unload|stop)
    unload_one nari
    unload_one nari-prompt
    sleep 1
    ollama ps || true
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || true
    ;;
  warm|load)
    curl -sS -m 300 -X POST "$BASE/api/chat" \
      -H 'Content-Type: application/json' \
      -d '{"model":"nari:latest","stream":false,"think":false,"messages":[{"role":"user","content":"hi"}]}' \
      | python3 -c 'import sys,json; j=json.load(sys.stdin); print((j.get("message") or {}).get("content","")[:80]); print("total_s", round((j.get("total_duration") or 0)/1e9,1))'
    ollama ps || true
    ;;
  *)
    echo "Usage: $0 {status|unload|warm}"
    exit 1
    ;;
esac
