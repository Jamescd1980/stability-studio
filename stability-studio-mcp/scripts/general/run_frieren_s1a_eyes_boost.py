"""Eyes-only Forge polish on Stage1 still → 720 MoE s1a comparison (keeps s1a_play.mp4)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402
from studio.forge_backend import forge_is_reachable, refine_image_forge, switch_stills_backend  # noqa: E402

from frieren_tease_i2v_kit import BEATS, CLIPS_DIR, EYE_LOCK, HANDS_BOTH, MOUTH_OK, NEG, STAGE1  # noqa: E402
from recycle_path import recycle  # noqa: E402

EYES_STILL = STAGE1.parent / "01_Frieren_Stage1_eyes.png"
CLIP_NAME = "s1a_play_eyes.mp4"

STILL_PROMPT = (
    "nb_frieren, frieren, nude elf girl, sitting on bed legs spread, "
    "same pose same body, detailed anime eyes, sharp teal iris texture, "
    "bright specular catchlights, lively focused gaze, sharp pupils, "
    "matte skin, twin tails, red teardrop earrings, soft daylight bedroom, "
    "masterpiece, best quality, <lora:Frieren:0.8>, "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.85>"
)
STILL_NEG = (
    "lowres, bad anatomy, blurry, watermark, text, "
    "dull eyes, dead eyes, glassy eyes, empty eyes, deformed eyes, "
    "soft eyes, muddy iris, star pupils"
)
AD_PROMPT = (
    "nb_frieren, detailed anime eyes, sharp teal iris texture, "
    "bright catchlights, lively focused gaze, sharp pupils, "
    "perfect eyes, eye_focus, <lora:Frieren:0.7>, "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.9>"
)


def main() -> int:
    cfg = load_config()
    if not STAGE1.is_file():
        print(f"missing {STAGE1}", flush=True)
        return 1

    print("SWITCH forge…", flush=True)
    sw = switch_stills_backend(cfg, backend="forge", wait=True)
    print(json.dumps({k: sw.get(k) for k in ("ok", "error")}, indent=2), flush=True)
    if not forge_is_reachable(cfg):
        print("Forge not reachable", flush=True)
        return 1

    print("EYES polish", STAGE1.name, "→", EYES_STILL.name, flush=True)
    r = refine_image_forge(
        cfg,
        image_path=str(STAGE1),
        prompt=STILL_PROMPT,
        negative_prompt=STILL_NEG,
        checkpoint="waijfu_alpha.safetensors",
        denoising_strength=0.07,  # lock body/pose
        steps=28,
        cfg_scale=5.5,
        seed=-1,
        adetailer=True,
        ad_model="mediapipe_face_mesh_eyes_only",
        ad_prompt=AD_PROMPT,
        ad_negative="dull eyes, dead eyes, glassy eyes, blurry eyes, deformed eyes, soft eyes",
        ad_denoising_strength=0.40,
        ad_dilate_erode=2,
        ad_mask_padding=16,
    )
    if not r.get("ok") or not r.get("saved_files"):
        print(json.dumps(r, indent=2)[:2500], flush=True)
        return 2
    shutil.copy2(r["saved_files"][0], EYES_STILL)
    print("OK still", EYES_STILL, flush=True)

    print("SWITCH comfy…", flush=True)
    sw = switch_stills_backend(cfg, backend="comfy", wait=True)
    print(json.dumps({k: sw.get(k) for k in ("ok", "error", "comfyui_running")}, indent=2), flush=True)

    beat = BEATS["s1a_play"]
    prompt = (
        f"{HANDS_BOTH}, "
        "gentle breast bounce, twin tails swaying, subtle hip movement, "
        f"{EYE_LOCK}, {MOUTH_OK}, "
        "steady camera, natural daylight"
    )
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    print("I2V from eyes still →", CLIPS_DIR / CLIP_NAME, flush=True)
    result = eng.generate_video(
        prompt=prompt,
        mode="i2v",
        negative_prompt=NEG,
        workflow_id="i2v",
        content_rating="open",
        image_path=str(EYES_STILL),
        num_frames=int(beat.get("num_frames") or 65),
        frame_rate=16.0,
        use_painter_i2v=False,
        smooth_motion=False,
        motion_amplitude=1.12,
    )
    saved = result.get("saved_files") or []
    if not saved:
        print("FAIL no video", json.dumps({k: result.get(k) for k in ("error", "workflow", "moe")}, indent=2), flush=True)
        return 2

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    dest = CLIPS_DIR / CLIP_NAME
    if dest.is_file():
        recycle(dest)
    src = Path(str(saved[0]))
    shutil.move(str(src), str(dest))
    twin = Path(r"D:\ComfyBox Images and Videos\Video") / src.name
    if twin.is_file() and twin.resolve() != dest.resolve():
        recycle(twin)

    out = {
        "ok": True,
        "eyes_still": str(EYES_STILL),
        "keeper": str(CLIPS_DIR / "s1a_play.mp4"),
        "comparison": str(dest),
        "width": result.get("width"),
        "height": result.get("height"),
        "moe": result.get("moe"),
    }
    (ROOT / "outputs" / "frieren_s1a_eyes_boost.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
