"""Promote current Saloon / Wild Fern keepers into Theater Jobs layout.

Images → Images\\Theater Jobs\\<Scene>\\Stills\\
Video  → Video\\Theater Jobs\\<Scene>\\{Work|Completed Scene}\\
User Import originals stay (user drops). Agent scratch + duplicate copies → Recycle Bin.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(r"D:\ComfyBox Images and Videos")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "general"))
try:
    from recycle_path import recycle  # type: ignore
except Exception:
    def recycle(p: Path) -> None:  # noqa: N802
        p = Path(p)
        if p.exists():
            # fallback: send via PowerShell later — delete only as last resort forbidden
            raise RuntimeError(f"recycle_path unavailable for {p}")


def ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def move_file(src: Path, dest: Path, *, overwrite: bool = False) -> str:
    if not src.is_file():
        return f"skip missing {src}"
    ensure(dest.parent)
    if dest.exists():
        if overwrite:
            recycle(dest)
        elif dest.stat().st_size == src.stat().st_size:
            try:
                recycle(src)
            except Exception as e:
                return f"dedupe but recycle locked {src.name}: {e}"
            return f"dedupe recycle src (same size) {src.name} -> already at {dest}"
        else:
            return f"skip exists different {dest}"
    try:
        shutil.move(str(src), str(dest))
    except PermissionError:
        try:
            shutil.copy2(src, dest)
            return f"copied (src locked) {src.name} -> {dest}"
        except Exception as e:
            return f"locked skip {src.name}: {e}"
    return f"moved {src} -> {dest}"


def copy_file(src: Path, dest: Path, *, overwrite: bool = False) -> str:
    if not src.is_file():
        return f"skip missing {src}"
    ensure(dest.parent)
    if dest.exists() and not overwrite:
        if dest.stat().st_size == src.stat().st_size:
            return f"ok already {dest.name}"
        return f"skip exists different {dest}"
    if dest.exists() and overwrite:
        recycle(dest)
    shutil.copy2(src, dest)
    return f"copied {src.name} -> {dest}"


def main() -> int:
    log: list[str] = []
    saloon_stills = ensure(ROOT / "Images/Theater Jobs/Saloon/Stills")
    saloon_forge = ensure(saloon_stills / "forge_soften")
    saloon_completed = ensure(ROOT / "Video/Theater Jobs/Saloon/Completed Scene")
    saloon_work = ensure(ROOT / "Video/Theater Jobs/Saloon/Work")
    saloon_work_logs = ensure(saloon_work / "logs")

    wf_stills = ensure(ROOT / "Images/Theater Jobs/Where the Wild Fern Moans/Stills")
    wf_forge = ensure(wf_stills / "forge_soften")
    wf_approved = ensure(wf_stills / "Approved")

    # --- Saloon forge soften (good) ---
    hero = ROOT / "User Import/Frieren Sex Sceens/scene_packs/Frieren Saloon/hero_forge"
    for src in sorted(hero.glob("*_forge_soften.png")):
        log.append(move_file(src, saloon_forge / src.name))

    # leave pack originals in User Import; recycle agent scratch
    rgb_tmp = hero / "_rgb_tmp"
    if rgb_tmp.is_dir():
        for f in rgb_tmp.rglob("*"):
            if f.is_file():
                recycle(f)
                log.append(f"recycle scratch {f.name}")
        try:
            rgb_tmp.rmdir()
        except OSError:
            pass
    for junk in (
        "_overnight.log",
        "_overnight.err.log",
        "_forge_all_local_batch.jsonl",
        "_forge_all_local_summary.json",
        "BJ02_smoke.png",
    ):
        p = hero / junk
        if p.is_file():
            recycle(p)
            log.append(f"recycle {junk}")

    # loose User Import duplicates of Saloon BJ02
    for name in ("Saloon_BJ02_forge_soften.png", "Saloon_BJ02_game.png"):
        p = ROOT / "User Import" / name
        if p.is_file():
            # ensure forge still already in Stills
            if name.endswith("forge_soften.png"):
                log.append(copy_file(p, saloon_forge / "BJ02_forge_soften.png"))
            recycle(p)
            log.append(f"recycle loose {name}")

    # --- Wild Fern forge soften + Approved keepers ---
    wf_rev_forge = ROOT / "Images/Theater Jobs/Where the Wild Fern Moans/review/forge_soften"
    for src in sorted(wf_rev_forge.glob("*_forge_soften.png")):
        log.append(move_file(src, wf_forge / src.name))
    for junk in ("_overnight.log", "_overnight.err.log", "_forge_soften_summary.json"):
        p = wf_rev_forge / junk
        if p.is_file():
            recycle(p)
            log.append(f"recycle {p.name}")
    rgb2 = wf_rev_forge / "_rgb_tmp"
    if rgb2.is_dir():
        for f in rgb2.rglob("*"):
            if f.is_file():
                recycle(f)
                log.append(f"recycle scratch {f.name}")

    wf_rev_approved = ROOT / "Images/Theater Jobs/Where the Wild Fern Moans/review/Approved"
    if wf_rev_approved.is_dir():
        for src in sorted(wf_rev_approved.glob("*.png")):
            log.append(copy_file(src, wf_approved / src.name))

    # --- Saloon video: Approved → Completed Scene; rest of Ready → Work ---
    legacy = ROOT / "Video/Frieren/Saloon/Ready for Post Production"
    approved = legacy / "Approved"
    if approved.is_dir():
        for src in sorted(approved.glob("*.mp4")):
            # strip bright seedvr suffix for cleaner completed names where obvious
            dest_name = src.name
            log.append(move_file(src, saloon_completed / dest_name))

    # known keeper / work clips sitting in Ready root
    work_names = [
        "BJ01.mp4",
        "BJ01_wan_flf_bob_samestill.mp4",
        "BJ02.mp4",
        "SS01_pingpong.mp4",
        "SS02_LC01_08s_pingpong_long_4x.mp4",
        "SS03_1_v2_T1.mp4",
        "SS03_2_v2_COCK_R1b.mp4",
        "SS03_3_1_loop.mp4",
        "SS03_3_2_loop.mp4",
        "SS04_001_v3.mp4",
        "SS04_002_v3.mp4",
        "SS04_1_v2_T13.mp4",
    ]
    for name in work_names:
        src = legacy / name
        if src.is_file():
            log.append(move_file(src, saloon_work / name))

    # BJ02 flf outputs / notes
    for src in legacy.glob("BJ02_flf*"):
        if src.is_file():
            log.append(move_file(src, saloon_work / src.name))
    for src in legacy.glob("_bj02*"):
        if src.is_file():
            log.append(move_file(src, saloon_work_logs / src.name))

    latest = ROOT / "Video/Frieren/Saloon/SS04_002_latest_wan.mp4"
    if latest.is_file():
        log.append(move_file(latest, saloon_work / "SS04_002_latest_wan.mp4"))

    # duplicate bright_seedvr tree (same files as Approved) → recycle files
    bright = legacy / "_bright_seedvr"
    if bright.is_dir():
        for f in bright.rglob("*"):
            if f.is_file():
                recycle(f)
                log.append(f"recycle dup bright {f.name}")

    # Video root studio_agent dumps → Saloon Work (recent FLF) if present
    for src in sorted((ROOT / "Video").glob("studio_agent_wan22_flf*.mp4")):
        log.append(move_file(src, saloon_work / src.name))

    # README pointer in legacy Saloon
    readme = ROOT / "Video/Frieren/Saloon/README_MOVED.md"
    readme.write_text(
        "# Moved\n\n"
        "Keepers live under:\n"
        "- `Video\\Theater Jobs\\Saloon\\Completed Scene\\`\n"
        "- `Video\\Theater Jobs\\Saloon\\Work\\`\n"
        "- `Images\\Theater Jobs\\Saloon\\Stills\\`\n"
        "\n"
        "`Video\\Frieren\\Saloon\\` is legacy. New gens: promote out of `Video\\` root into Theater Jobs.\n",
        encoding="utf-8",
    )
    log.append(f"wrote {readme}")

    layout_note = ROOT / "Images/Theater Jobs/README.md"
    layout_note.write_text(
        "# Theater Jobs media\n\n"
        "- **Stills** = keepers / forge soften / approved CGs\n"
        "- **User Import** = human drops only (do not pile agent outputs there)\n"
        "- Video keepers = `Video\\Theater Jobs\\<Scene>\\Completed Scene\\`\n"
        "- Video WIP = `Video\\Theater Jobs\\<Scene>\\Work\\`\n"
        "- Comfy/Forge may land as `studio_agent_*` in `Video\\` or `Images\\` root — promote ASAP\n",
        encoding="utf-8",
    )
    log.append(f"wrote {layout_note}")

    out = ROOT / "logs" / "promote_theater_jobs_keepers.json"
    ensure(out.parent)
    out.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"DONE {len(log)} actions -> {out}", flush=True)
    for line in log:
        print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
