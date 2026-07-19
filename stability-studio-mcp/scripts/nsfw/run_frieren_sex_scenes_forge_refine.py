"""Forge-refine Frieren Sex Scenes imports → _refined/pass1 (no overwrite)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge, switch_stills_backend  # noqa: E402

from frieren_sex_scenes_refine_kit import (  # noqa: E402
    AD_PROMPT,
    CHECKPOINT,
    CFG,
    DENOISE,
    GLOBAL_PROMPT,
    IMPORT_DIR,
    NEGATIVE,
    OUT_DIR,
    PILOT,
    SOURCES,
    STEPS,
)


def _copy_named(src_saved: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_saved, dest)
    return dest


def refine_one(cfg: dict, name: str) -> dict:
    src = IMPORT_DIR / name
    if not src.is_file():
        return {"ok": False, "name": name, "error": f"missing: {src}"}
    stem = Path(name).stem
    dest = OUT_DIR / f"{stem}_forge.png"
    print(f"REFINE {name} → {dest.name}", flush=True)
    result = refine_image_forge(
        cfg,
        image_path=str(src),
        prompt=GLOBAL_PROMPT,
        negative_prompt=NEGATIVE,
        checkpoint=CHECKPOINT,
        denoising_strength=DENOISE,
        steps=STEPS,
        cfg_scale=CFG,
        seed=-1,
        adetailer=True,
        ad_prompt=AD_PROMPT,
    )
    if not result.get("ok"):
        return {"ok": False, "name": name, "result": result}
    saved = result.get("saved_files") or []
    if not saved:
        return {"ok": False, "name": name, "error": "no saved_files", "result": result}
    copied = _copy_named(Path(saved[0]), dest)
    return {
        "ok": True,
        "name": name,
        "source": str(src),
        "output": str(copied),
        "forge_saved": saved,
        "denoising_strength": DENOISE,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help=f"Only refine {PILOT}")
    ap.add_argument("--name", default="", help="Refine a single filename")
    ap.add_argument("--skip-switch", action="store_true")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_switch:
        print("SWITCH forge…", flush=True)
        sw = switch_stills_backend(cfg, backend="forge", wait=True)
        print(json.dumps({k: sw.get(k) for k in ("ok", "backend", "error", "running")}, indent=2), flush=True)
        if not sw.get("ok") and not sw.get("running"):
            # switch may return differently; continue if forge already up
            if not (sw.get("forge") or {}).get("running") and sw.get("ok") is False:
                print("Forge switch failed", flush=True)
                print(json.dumps(sw, indent=2)[:4000], flush=True)
                return 1

    if args.pilot:
        names = [PILOT]
    elif args.name:
        names = [args.name]
    else:
        names = list(SOURCES)

    if args.skip_existing:
        kept = []
        for name in names:
            dest = OUT_DIR / f"{Path(name).stem}_forge.png"
            if dest.is_file():
                print(f"SKIP existing {dest.name}", flush=True)
            else:
                kept.append(name)
        names = kept

    results = []
    for name in names:
        r = refine_one(cfg, name)
        results.append(r)
        print(json.dumps({k: r.get(k) for k in ("ok", "name", "output", "error")}, indent=2), flush=True)
        if not r.get("ok"):
            print(json.dumps(r, indent=2)[:3000], flush=True)

    out_json = ROOT / "outputs" / "frieren_sex_scenes_forge_refine.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"DONE {ok}/{len(results)} → {OUT_DIR}", flush=True)
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
