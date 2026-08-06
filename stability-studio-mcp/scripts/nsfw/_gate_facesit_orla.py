"""Quick Orla-VL gate for facesit role lock."""
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
    "Look carefully at hair colors. "
    "In one short sentence: who is sitting on whose face "
    "(purple-haired Fern vs blonde Darkness)? "
    "Also say if anyone looks back over their shoulder."
)


def ask(path: Path) -> dict:
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
        return json.loads(r.read().decode())


def main() -> int:
    for p in sorted(OUT.glob("*.png")):
        print("====", p.name, flush=True)
        data = ask(p)
        print("RESP:", (data.get("response") or "").strip(), flush=True)
        think = (data.get("thinking") or "").strip()
        if think:
            print("THINK:", think[:400], flush=True)
        print(flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
