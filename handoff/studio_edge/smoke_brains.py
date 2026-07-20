#!/usr/bin/env python3
"""Quick reachability smoke for Myra gofor / Nari / Orla."""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def get_json(url: str, timeout: float = 8.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def chat(base: str, model: str, text: str, timeout: float = 90.0) -> str:
    root = base[:-3] if base.endswith("/v1") else base.rstrip("/")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "think": False,
        "options": {"num_predict": 24},
    }
    req = urllib.request.Request(
        f"{root}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return ((d.get("message") or {}).get("content") or "").strip()


def main() -> int:
    checks = [
        ("Pi Ollama tags", "http://127.0.0.1:11434/api/tags"),
        ("Nari tags", "http://192.168.50.57:11434/api/tags"),
        ("Orla tags", "http://192.168.50.42:11434/api/tags"),
        ("Orla tools", "http://192.168.50.42:11436/status"),
    ]
    for label, url in checks:
        try:
            data = get_json(url)
            if "models" in data:
                names = [m.get("name") for m in data["models"]]
                print(f"OK  {label}: {names}")
            else:
                print(f"OK  {label}: {data}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {label}: {exc}")

    for label, base, model in (
        ("gofor", "http://127.0.0.1:11434", "myra-gofor"),
        ("nari", "http://192.168.50.57:11434", "nari"),
        ("orla", "http://192.168.50.42:11434", "orla"),
    ):
        try:
            reply = chat(base, model, "Say ready in one word.")
            print(f"OK  chat {label}: {reply!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL chat {label}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
