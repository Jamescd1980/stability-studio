#!/usr/bin/env bash
# Start nothink proxy (OI → :11435 → Ollama :11434).
set -euo pipefail
cd "$(dirname "$0")"
pkill -f 'ollama_nothink_proxy.py' 2>/dev/null || true
nohup python3 ollama_nothink_proxy.py >> /tmp/ollama_nothink_proxy.log 2>&1 &
echo "started pid $!  log /tmp/ollama_nothink_proxy.log"
sleep 0.5
curl -s -o /dev/null -w "proxy_health_http=%{http_code}\n" http://127.0.0.1:11435/api/tags || true
