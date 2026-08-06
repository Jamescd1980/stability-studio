"""SS02 Try 2 — manual genital mask inpaint (already-in) + Missionary Sex thrust."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

from recycle_path import recycle  # noqa: E402

START = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\Frieren Saloon\SS02.png"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
DIAG_DIR = ROOT / "outputs" / "saloon_diag_frames" / "ss02_try2"
BEAT_ID = "SS02_try2_sex_on_painted"

NEG = (
    "fast motion, violent slam, "
    "hand movement, waving hands, grabbing randomly, flailing hands, "
    "moving hands, shifting grip, squeezing thighs, extra hands, four hands, "
    "side to side, lateral sway, swinging sideways, left right wobble, "
    "hip shake, hip wiggle, shaking hips, body shake, "
    "penis pulse, pulsing cock, throbbing only, shaft pulse without thrust, "
    "jitter, shaky, wobble, vibrating, flicker, "
    "morphing vagina, shifting labia, jumping genitals, anatomy flicker, "
    "full withdrawal, penis slides out, cock leaves pussy, empty vagina, "
    "deformed vagina, melting pussy, morphing genitals, "
    "deflating penis, disappearing shaft, blob penis, "
    "penis outside, no penetration, grinding only, floating cock, "
    "melting face, morphing face, "
    "extra limbs, wrong anatomy, "
    "talking, lip sync, cartoon, chibi, "
    "camera, dslr, camcorder, lens"
)

SEX_LORAS = [
    {
        "id": "missionary_sex_high",
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "high",
    },
    {
        "id": "missionary_sex_low",
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 1.0,
        "branch": "low",
    },
]

INPAINT_PROMPT = (
    "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
    "nsfw, pov shot, 1girl, frieren, silver hair, twin tails, pointed ears, "
    "naked, flushed cheeks, look of pleasure, "
    "cock buried mid-depth inside her pussy, shaft visible, labia wrapped around penis, "
    "vaginal penetration, hands gripping her inner thighs, saloon bar background, "
    "warm lighting, steady view"
)

INPAINT_NEG = (
    "lowres, bad anatomy, bad hands, extra fingers, deformed face, blurry, "
    "worst quality, watermark, text, clothing, shirt, "
    "tip only, cock at entrance, empty vagina, penis outside, floating cock, "
    "melting genitals, blob penis, wrong hair color, wrong setting, bedroom"
)

SEX_PROMPT = (
    "nsfw, A naked man and a naked woman having sex. "
    "He thrusts his penis in and out of her vagina. a pov shot. "
    "cock stays inside, partial withdraw only, vaginal penetration, steady view"
)


def make_genital_mask(src: Path, mask_path: Path) -> Path:
    """Bottom-center box mask covering vulva + lower shaft (white=inpaint)."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    # POV genital zone: lower ~30% height, center ~45% width
    x0 = int(w * 0.28)
    x1 = int(w * 0.72)
    y0 = int(h * 0.62)
    y1 = int(h * 0.98)
    draw.rectangle([x0, y0, x1, y1], fill=255)
    # soften edges with slight feather via blur substitute (expand inner keep)
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(mask_path)
    return mask_path


def main() -> int:
    if not START.is_file():
        print(f"missing {START}", flush=True)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))

    mask_path = DIAG_DIR / "ss02_genital_mask.png"
    make_genital_mask(START, mask_path)
    print("mask", mask_path, flush=True)

    painted_dest = OUT_DIR / "SS02_already_in_painted.png"
    print("===== INPAINT already-in still =====", flush=True)
    inpaint_result = engine.inpaint_advanced(
        image_path=str(START),
        prompt=INPAINT_PROMPT,
        negative_prompt=INPAINT_NEG,
        mask_path=str(mask_path),
        mask_region="none",
        style="anime",
        denoising_strength=0.42,
        steps=28,
        cfg=5.5,
        seed=42,
    )
    saved_inpaint = inpaint_result.get("saved_files") or []
    if not saved_inpaint:
        summary = {"ok": False, "stage": "inpaint", "error": "no saved_files", "result": inpaint_result}
        out_json = ROOT / "outputs" / f"saloon_{BEAT_ID}_i2v.json"
        out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2), flush=True)
        return 2

    src_painted = Path(str(saved_inpaint[0]))
    if painted_dest.is_file():
        recycle(painted_dest)
    shutil.copy2(src_painted, painted_dest)
    print("painted still", painted_dest, flush=True)

    print(f"===== I2V {BEAT_ID} quality amp=0.32 frames=33 =====", flush=True)
    result = engine.generate_video(
        prompt=SEX_PROMPT,
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(painted_dest),
        num_frames=33,
        frame_rate=16.0,
        loras=SEX_LORAS,
        moe_preset="quality",
        smooth_motion=False,
        motion_amplitude=0.32,
    )

    saved = result.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]
    dest = OUT_DIR / f"{BEAT_ID}.mp4"
    promoted = None
    for p in saved:
        src = Path(str(p))
        if src.is_file() and src.suffix.lower() == ".mp4":
            if dest.is_file():
                recycle(dest)
            shutil.move(str(src), str(dest))
            promoted = dest
            break

    summary = {
        "ok": bool(promoted),
        "experiment": BEAT_ID,
        "approach": "manual PIL genital mask inpaint -> Missionary Sex on buried still",
        "differs_from_try1": "Try1=Insertion bury on tip still; Try2=state change via inpaint then Sex LoRA",
        "image": str(painted_dest),
        "source_still": str(START),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": 0.32,
        "frames": 33,
        "loras": SEX_LORAS,
        "prompt": SEX_PROMPT,
        "inpaint_denoise": 0.42,
        "result_ok": result.get("ok"),
    }
    out_json = ROOT / "outputs" / f"saloon_{BEAT_ID}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
