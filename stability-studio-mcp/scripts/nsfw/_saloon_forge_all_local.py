"""Overnight local-Forge soften+ADetailer pass for all Saloon pack stills."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge  # noqa: E402

PACK = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\Frieren Saloon"
)
OUT = PACK / "hero_forge"
FORGE = "http://127.0.0.1:7860"
LOG = OUT / "_forge_all_local_batch.jsonl"
SUMMARY = OUT / "_forge_all_local_summary.json"

# skip prior forge outputs / tiny maxinsert probe
SKIP = {
    "SS03_3_v2_T1_maxinsert.png",
}

PROMPT_BODY = (
    "masterpiece, best quality, anime++, Frieren, silver hair, green eyes, "
    "soft diffused lighting, gentle rim light, matte skin, reduced specular, "
    "natural eyes, clean iris, round pupils, consistent face"
)
PROMPT_ORAL = (
    "masterpiece, best quality, anime++, Frieren, soft diffused lighting, "
    "matte skin, natural eyes, clean iris, round pupils, no glare"
)
NEG = (
    "overexposed, harsh specular, oily skin glare, blown highlights, "
    "lens flare, eye flare, sparkle eyes, glowing eyes, starburst eyes, "
    "plastic skin, blurry, bad anatomy, extra fingers, "
    "camera, dslr, camcorder, watermark, text"
)
AD_FACE = (
    "Frieren face, green eyes, soft diffuse catchlights, detailed iris, "
    "round pupils, clean eyes, soft lighting, natural skin"
)
AD_EYES = (
    "natural anime eyes, soft diffuse catchlights, detailed iris, "
    "round pupils, clean eyes, no glare, no flare"
)
AD_NEG = (
    "lens flare, eye flare, bright catchlights, sparkle eyes, glowing eyes, "
    "starburst, star pupils, overexposed eyes, specular eyes, oily glare"
)


def wait_forge(timeout_s: int = 900) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=5).ok:
                print(f"Forge up after {time.time()-t0:.0f}s", flush=True)
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise RuntimeError("Local Forge not up")


def pick_checkpoint() -> str:
    models = requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=60).json()
    titles = [m.get("title") or m.get("model_name") or "" for m in models]
    for prefer in ("waijfu_alpha", "waiNSFW", "illustrious", "animagine"):
        for t in titles:
            if prefer.lower() in t.lower():
                return t
    if not titles:
        raise RuntimeError("No Forge checkpoints found")
    return titles[0]


def is_oral(name: str) -> bool:
    n = name.lower()
    return n.startswith("bj") or "post bj" in n


def rgb_temp(src: Path, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / src.name
    with Image.open(src) as im:
        im.convert("RGB").save(dest, format="PNG")
    return dest


def append_log(row: dict) -> None:
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp_dir = OUT / "_rgb_tmp"
    wait_forge()

    ckpt = pick_checkpoint()
    print("checkpoint:", ckpt, flush=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": ckpt},
        timeout=600,
    )

    cfg = load_config()
    cfg.setdefault("forge", {})
    cfg["forge"]["url"] = FORGE
    cfg["forge"]["generate_timeout_seconds"] = 1800

    # monkey-patch: forge_backend refuses if remote comfy reachable — disable that check locally
    import studio.forge_backend as fb
    import studio.gpu_backend as gb

    gb.comfyui_is_reachable = lambda _cfg=None: False  # type: ignore
    fb.comfyui_is_reachable = lambda _cfg=None: False  # type: ignore

    srcs = sorted(
        p
        for p in PACK.glob("*.png")
        if p.name not in SKIP and not p.name.endswith("_forge_soften.png")
    )
    print(f"jobs: {len(srcs)}", flush=True)

    results = []
    for i, src in enumerate(srcs, 1):
        stem = src.stem.replace(" ", "_")
        dest = OUT / f"{stem}_forge_soften.png"
        if dest.is_file() and dest.stat().st_size > 50_000:
            print(f"[{i}/{len(srcs)}] SKIP exists {dest.name}", flush=True)
            row = {"name": src.name, "ok": True, "path": str(dest), "skipped": True}
            results.append(row)
            append_log(row)
            continue

        mode = "oral" if is_oral(src.name) else "body"
        print(f"[{i}/{len(srcs)}] {src.name} ({mode})", flush=True)
        try:
            rgb = rgb_temp(src, tmp_dir)
            if mode == "oral":
                r = refine_image_forge(
                    cfg,
                    image_path=str(rgb),
                    prompt=PROMPT_ORAL,
                    negative_prompt=NEG,
                    checkpoint=ckpt,
                    denoising_strength=0.08,
                    steps=24,
                    cfg_scale=5.0,
                    seed=62024,
                    adetailer=True,
                    ad_model="mediapipe_face_mesh_eyes_only",
                    ad_prompt=AD_EYES,
                    ad_negative=AD_NEG,
                    ad_denoising_strength=0.32,
                    ad_dilate_erode=2,
                    ad_mask_padding=20,
                )
            else:
                r = refine_image_forge(
                    cfg,
                    image_path=str(rgb),
                    prompt=PROMPT_BODY,
                    negative_prompt=NEG,
                    checkpoint=ckpt,
                    denoising_strength=0.22,
                    steps=28,
                    cfg_scale=5.0,
                    seed=62024,
                    adetailer=True,
                    ad_model="face_yolov8n.pt",
                    ad_prompt=AD_FACE,
                    ad_negative=AD_NEG,
                    ad_denoising_strength=0.30,
                    ad_dilate_erode=4,
                    ad_mask_padding=32,
                )
            if not r.get("ok") or not r.get("saved_files"):
                raise RuntimeError(r.get("error") or "no saved_files")
            import shutil

            shutil.copy2(r["saved_files"][0], dest)
            row = {"name": src.name, "ok": True, "path": str(dest), "mode": mode}
            print("  OK", dest.name, flush=True)
        except Exception as e:
            row = {"name": src.name, "ok": False, "error": str(e), "mode": mode}
            print("  FAIL", e, flush=True)
        results.append(row)
        append_log(row)

    SUMMARY.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok_n = sum(1 for x in results if x.get("ok"))
    print(f"DONE {ok_n}/{len(results)} -> {OUT}", flush=True)
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
