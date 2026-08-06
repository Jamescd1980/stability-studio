"""Redo Saloon SS sex beats only (BJ leave-as-is). One beat per CLI arg recommended."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))
sys.path.insert(0, str(ROOT / "scripts" / "nsfw"))

from recycle_path import recycle  # noqa: E402
from run_saloon_i2v_chain import BEATS, OUT_DIR, run_beat  # noqa: E402
from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

# Overnight default order: doggy fix → missionary improve → insert thrust.
# Never BJ.
REDO_IDS = ["SS03", "SS02", "SS01"]


def main() -> int:
    only = sys.argv[1:] or REDO_IDS
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    by_id = {b["id"]: b for b in BEATS}
    ok = True
    print(f"overnight redo order: {only}", flush=True)
    for bid in only:
        if bid.upper().startswith("BJ"):
            print(f"skip {bid} (BJ leave-as-is)", flush=True)
            continue
        beat = by_id.get(bid)
        if not beat:
            print(f"unknown {bid}", flush=True)
            ok = False
            continue
        dest = OUT_DIR / f"{bid}.mp4"
        if dest.is_file():
            recycle(dest)
            print(f"recycled old {dest.name}", flush=True)
        summary = run_beat(engine, beat)
        ok = ok and bool(summary.get("ok"))
        print(f"beat {bid} ok={summary.get('ok')} path={summary.get('path')}", flush=True)
    print("OVERNIGHT DONE ok=" + str(ok), flush=True)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
