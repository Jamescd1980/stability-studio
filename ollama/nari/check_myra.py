#!/usr/bin/env python3
import json
import time
import urllib.request

print("=== ollama ps ===")
print(urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=10).read().decode()[:500])

print("=== chat smoke ===")
t0 = time.time()
payload = {
    "model": "qwen3:1.7b",
    "messages": [{"role": "user", "content": "Say OK in one word."}],
    "stream": False,
    "think": False,
    "options": {"num_predict": 8},
}
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    msg = d.get("message") or {}
    print(
        "ok",
        round(time.time() - t0, 1),
        "s content=",
        repr(msg.get("content", "")[:120]),
        "thinking=",
        repr((msg.get("thinking") or "")[:120]),
    )
except Exception as e:
    print("FAIL", round(time.time() - t0, 1), "s", type(e).__name__, e)

print("=== log today ===")
with open("/tmp/myra.log", encoding="utf-8", errors="replace") as f:
    for line in f:
        if "2026-07-19" in line:
            print(line.rstrip())
