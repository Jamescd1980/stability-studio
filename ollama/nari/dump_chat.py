#!/usr/bin/env python3
import json
import sys
import urllib.request

model = sys.argv[1] if len(sys.argv) > 1 else "nari"
prompt = sys.argv[2] if len(sys.argv) > 2 else "Say hello in five words. Are you Myra?"
payload = {
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
    "stream": False,
    "think": False,
    "options": {"num_predict": 200},
}
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=180) as resp:
    data = json.load(resp)
msg = data.get("message", {})
print("CONTENT:", repr(msg.get("content", ""))[:1500])
print("THINKING:", repr(msg.get("thinking", ""))[:400])
print(
    "tokens", data.get("eval_count"),
    "total_ms", (data.get("total_duration") or 0) // 1_000_000,
)
