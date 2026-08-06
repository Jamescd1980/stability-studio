"""Gate facesit batch for known failure modes."""
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
PROMPT = (
    "NSFW still QA. Reply with short bullets only: "
    "roles (who on top), Fern eye color, under/fringe eye or hair color, "
    "wall color, any white semen stains yes/no, lookback yes/no, "
    "breast size small/medium/large, finish clean/mushy. One line each."
)


def ask(path: Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode()
    body = {
        "model": "orla-vl:latest",
        "prompt": PROMPT,
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 220},
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=360) as r:
        data = json.loads(r.read().decode())
    resp = (data.get("response") or "").strip()
    think = (data.get("thinking") or "").strip()
    return resp or think[:500]


def main() -> int:
    for p in sorted(OUT.glob("facesit_*.png")):
        print("====", p.name, flush=True)
        print(ask(p), flush=True)
        print(flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
