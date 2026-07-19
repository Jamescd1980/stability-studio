#!/usr/bin/env python3
"""Smoke test without think:false — matches Eric / dumb clients."""
import json
import urllib.request


def chat(model: str, prompt: str, num_predict: int = 160) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": num_predict},
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)


print("=== nari ===")
d = chat("nari", "Who are you? One sentence. Are you Myra?")
print(d.get("message", {}).get("content", "")[:800])
print("tokens", d.get("eval_count"), "ms", (d.get("total_duration") or 0) // 1_000_000)

print("=== nari-prompt ===")
d = chat(
    "nari-prompt",
    "Expand for Wan I2V: Frieren fingering herself slowly, medium shot, breathing harder.",
    num_predict=220,
)
print(d.get("message", {}).get("content", "")[:1200])
print("tokens", d.get("eval_count"), "ms", (d.get("total_duration") or 0) // 1_000_000)
