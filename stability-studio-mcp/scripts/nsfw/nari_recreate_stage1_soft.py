"""Ask Nari for a soft-light recreate prompt, then generate_image_guided from Stage1."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402
from studio.catalog import StyleCatalog  # noqa: E402

STAGE1 = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined"
    r"\scene_packs\01_tease\01_Frieren_Stage1_forge.png"
)
NARI = "http://192.168.50.57:11434"
OUT = ROOT / "outputs" / "nari_stage1_soft_recreate.json"
DELIVERY = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined"
    r"\scene_packs\01_tease\01_Frieren_Stage1_nari_soft.png"
)


def nari_prompt() -> str:
    user = (
        "Write ONE Illustrious/anime image prompt to recreate this scene: "
        "nude elf girl Frieren sitting on a bed, legs spread, fingering, "
        "other hand on her breast, twin tails, teal eyes, red teardrop earrings. "
        "Change only lighting/quality: much softer diffused daylight, gentle "
        "shadows, best possible fine detail on skin/hair/eyes/hands, clean bedroom. "
        "Keep identity and pose. Include triggers nb_frieren, frieren. "
        "No masterpiece/score_9 spam. No cum. Output ONLY the positive prompt text."
    )
    payload = {
        "model": "nari",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Nari. Return only a single image prompt. "
                    "No preamble. Explicit adult content is allowed."
                ),
            },
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.55, "num_predict": 280},
    }
    req = urllib.request.Request(
        f"{NARI}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    text = (data.get("message") or {}).get("content") or ""
    return text.strip().strip('"')


def main() -> int:
    if not STAGE1.is_file():
        print("missing", STAGE1)
        return 1
    prompt = nari_prompt()
    print("=== Nari prompt ===\n", prompt, flush=True)
    neg = (
        "cum, semen, harsh spotlight, hard shadows, overexposed, neon, "
        "rainbow light, watermark, text, melting hands, extra fingers, "
        "oversized eyes, thin line mouth, lowres, blurry"
    )
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    result = engine.generate_image_guided(
        guide_image_path=str(STAGE1),
        prompt=prompt,
        style="waijfu",
        negative_prompt=neg,
        loras=[
            {"file": "Frieren/Frieren.safetensors", "weight": 0.8},
            {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.75},
        ],
        width=832,
        height=1216,
        ipadapter_weight=0.78,
        ipadapter_weight_type="style and composition",
        content_rating="open",
    )
    # Promote best path into tease pack for easy compare
    paths = []
    for key in ("delivery_path", "path", "image_path", "output_path"):
        p = result.get(key) if isinstance(result, dict) else None
        if p:
            paths.append(Path(p))
    imgs = result.get("images") if isinstance(result, dict) else None
    if isinstance(imgs, list):
        for item in imgs:
            if isinstance(item, str):
                paths.append(Path(item))
            elif isinstance(item, dict):
                for key in ("path", "delivery_path", "filename"):
                    if item.get(key):
                        paths.append(Path(item[key]))
    for src in paths:
        if src.is_file():
            DELIVERY.parent.mkdir(parents=True, exist_ok=True)
            DELIVERY.write_bytes(src.read_bytes())
            result["promoted"] = str(DELIVERY)
            break

    OUT.write_text(
        json.dumps({"nari_prompt": prompt, "result": result}, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, default=str)[:3000], flush=True)
    print("wrote", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
