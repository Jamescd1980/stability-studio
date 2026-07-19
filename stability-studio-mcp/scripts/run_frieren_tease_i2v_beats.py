"""Generate Frieren Tease Wan I2V beats from kit; copy into Video/Frieren Tease/clips."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402
from studio.forge_backend import switch_stills_backend  # noqa: E402
from studio.wan_video_loras import check_wan_video_loras  # noqa: E402

from frieren_tease_i2v_kit import BEATS, CLIPS_DIR, NEG, STAGE1, VIDEO_DIR  # noqa: E402


def resolve_image(beat: dict) -> Path:
    img = Path(beat["image"])
    if img.is_file():
        return img
    # fallbacks
    name = img.name
    if "wet" in name and STAGE1.is_file():
        return STAGE1
    if STAGE1.is_file():
        return STAGE1
    raise FileNotFoundError(img)


def loras_available(cfg: dict, lora_ids: str) -> str:
    if not lora_ids:
        return ""
    ids = [x.strip() for x in lora_ids.split(",") if x.strip()]
    status = check_wan_video_loras(cfg, ids)
    missing = {m["id"] for m in status.get("missing") or []}
    keep = [i for i in ids if i not in missing]
    return ",".join(keep)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", default="s1a_play,s1b_wet,s1c_shudder", help="comma beat ids")
    ap.add_argument("--ensure-comfy", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    if args.ensure_comfy:
        print("SWITCH comfy…", flush=True)
        sw = switch_stills_backend(cfg, backend="comfy", wait=True)
        print(json.dumps({k: sw.get(k) for k in ("ok", "error", "comfyui_running", "ready")}, indent=2), flush=True)

    catalog = StyleCatalog(catalog_path(cfg), cfg)
    engine = GenerationEngine(cfg, catalog)

    beat_ids = [b.strip() for b in args.beats.split(",") if b.strip()]
    results = []
    for bid in beat_ids:
        beat = BEATS.get(bid)
        if not beat:
            results.append({"id": bid, "ok": False, "error": "unknown beat"})
            continue
        image = resolve_image(beat)
        loras = loras_available(cfg, beat.get("loras") or "")
        lora_list = [x.strip() for x in loras.split(",") if x.strip()] if loras else None
        lora_bundle = str(beat.get("lora_bundle") or "")
        print(f"\n===== I2V {bid} =====", flush=True)
        print(
            "image",
            image,
            "workflow",
            beat["workflow"],
            "loras",
            lora_list or "(none)",
            "bundle",
            lora_bundle or "(none)",
            flush=True,
        )
        try:
            result = engine.generate_video(
                prompt=beat["prompt"],
                mode="i2v",
                negative_prompt=NEG,
                workflow_id=beat["workflow"],
                content_rating="open",
                image_path=str(image),
                num_frames=int(beat.get("num_frames") or 65),
                frame_rate=16.0,
                lora_ids=lora_list,
                lora_bundle=lora_bundle,
                use_painter_i2v=False,
                smooth_motion=bool(beat.get("smooth_motion", False)),
                motion_amplitude=float(beat.get("motion_amplitude") or 1.08),
            )
        except Exception as exc:
            print(f"FAIL {bid}: {exc}", flush=True)
            results.append({"id": bid, "ok": False, "error": str(exc)})
            continue

        saved = result.get("saved_files") or result.get("video_path") or []
        if isinstance(saved, str):
            saved = [saved]
        copied = []
        for p in saved:
            src = Path(str(p))
            if not src.is_file():
                continue
            dest = CLIPS_DIR / f"{bid}_{src.name}"
            shutil.copy2(src, dest)
            copied.append(str(dest))
        # also common keys
        for key in ("output_path", "path", "mp4"):
            if result.get(key):
                src = Path(str(result[key]))
                if src.is_file():
                    dest = CLIPS_DIR / f"{bid}_{src.name}"
                    shutil.copy2(src, dest)
                    copied.append(str(dest))
        entry = {
            "id": bid,
            "ok": bool(copied) or bool(result.get("ok", True)),
            "image": str(image),
            "workflow": beat["workflow"],
            "loras": loras,
            "copied": copied,
            "raw_keys": list(result.keys()) if isinstance(result, dict) else [],
        }
        results.append(entry)
        print(json.dumps(entry, indent=2)[:2000], flush=True)

    summary = {"ok": all(r.get("ok") for r in results), "results": results}
    out = ROOT / "outputs" / "frieren_tease_i2v_beats.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nDONE", out, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
