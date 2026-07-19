#!/usr/bin/env bash
set -euo pipefail

echo "=== nari smoke ==="
curl -s http://127.0.0.1:11434/api/chat \
  -d '{"model":"nari","messages":[{"role":"user","content":"Who are you? One sentence. Are you Myra?"}],"stream":false,"options":{"num_predict":80}}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message",{}).get("content","")); print("tokens", d.get("eval_count"), "load_ms", (d.get("load_duration") or 0)//1_000_000, "total_ms", (d.get("total_duration") or 0)//1_000_000)'

echo "=== nari-prompt smoke ==="
curl -s http://127.0.0.1:11434/api/chat \
  -d '{"model":"nari-prompt","messages":[{"role":"user","content":"Expand for Wan I2V: Frieren fingering herself slowly, medium shot, breathing harder."}],"stream":false,"options":{"num_predict":220}}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message",{}).get("content","")); print("tokens", d.get("eval_count"), "total_ms", (d.get("total_duration") or 0)//1_000_000)'

echo "=== tags ==="
curl -s http://127.0.0.1:11434/api/tags | python3 -c 'import sys,json; print([m["name"] for m in json.load(sys.stdin).get("models",[])])'

echo "=== rocm snapshot (should stay free for Comfy) ==="
rocm-smi --showuse 2>/dev/null | head -25 || true
