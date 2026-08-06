"""Recycle obsolete Saloon media; keep bright masters + game keepers + _bright_seedvr."""
from __future__ import annotations

import shutil
from pathlib import Path

from send2trash import send2trash

READY = Path(
    r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon\Ready for Post Production"
)
SALOON = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
GAME = Path(r"D:\Bad boy\TheaterJobs\game\videos\Movie_Saloon")
APPROVED = READY / "Approved"
TEMP = Path(r"D:\ComfyBox Images and Videos\temp")

STEMS = [
    "BJ01",
    "BJ02",
    "SS01",
    "SS02",
    "SS03_1",
    "SS03_2",
    "SS03_3_1",
    "SS03_3_2",
    "SS04",
    "SS04_001",
    "SS04_002",
]

KEEP_READY_MP4 = {
    "BJ01.mp4",
    "BJ01_wan_flf_bob_samestill.mp4",
    "BJ02.mp4",
    "SS01_pingpong.mp4",
    "SS02_LC01_08s_pingpong_long_4x.mp4",
    "SS03_1_v2_T1.mp4",
    "SS03_2_v2_COCK_R1b.mp4",
    "SS03_3_1_loop.mp4",
    "SS03_3_2_loop.mp4",
    "SS04_1_v2_T13.mp4",
    "SS04_001_v3.mp4",
    "SS04_002_v3.mp4",
}

trashed: list[str] = []
skipped: list[str] = []


def trash(p: Path, reason: str) -> None:
    if not p.exists():
        return
    try:
        send2trash(str(p))
        trashed.append(f"{reason}: {p}")
        label = p.name + ("/" if p.is_dir() else "")
        print("TRASH", reason, label, flush=True)
    except Exception as e:
        skipped.append(f"{p}: {e}")
        print("SKIP", p, e, flush=True)


def main() -> int:
    # 1) Game backups
    for p in GAME.glob("*"):
        if p.is_file() and ".bak" in p.name:
            trash(p, "game-bak")

    # 2) WIP / old polish dirs
    for name in (
        "_bj01_flf",
        "_bj01_forge",
        "_bj01_review",
        "_bj01_wan157_gate",
        "_BJ01_wan_flf_bob_samestill_pingpong_work",
        "_gate_BJ01_wan_00157_headbob",
        "_seedvr_only",
        "polished",
    ):
        trash(READY / name, "wip-dir")

    # 3) Ready top dim / old seedvr / rife (keep bright raw masters)
    for p in READY.glob("*.mp4"):
        if p.name in KEEP_READY_MP4:
            continue
        nl = p.name.lower()
        if "dim" in nl or "seedvr" in nl or "rife" in nl or p.name.startswith("_"):
            trash(p, "ready-old-mp4")

    for p in READY.iterdir():
        if p.is_file() and p.suffix.lower() in {".txt", ".json", ".log"} and p.name.startswith("_"):
            trash(p, "ready-log")

    # 4) Replace Approved with current game bright pack
    for p in list(APPROVED.glob("*")):
        if p.is_file():
            trash(p, "old-approved")
    APPROVED.mkdir(parents=True, exist_ok=True)

    for stem in STEMS:
        src = GAME / f"{stem}.mp4"
        if not src.is_file():
            print("MISSING game", stem, flush=True)
            continue
        if stem == "BJ01":
            dest = APPROVED / "BJ01_wan_flf_bob_samestill_loop3s.mp4"
        elif stem == "SS03_1":
            dest = APPROVED / "SS03_1_v2_T1_bright.mp4"
        else:
            dest = APPROVED / f"{stem}_bright_seedvr2_1080.mp4"
        shutil.copy2(src, dest)
        print("APPROVED", dest.name, dest.stat().st_size, flush=True)

    # 5) Saloon root clutter
    for p in SALOON.glob("*.mp4"):
        trash(p, "saloon-root-dup")
    for p in SALOON.glob("*.png"):
        trash(p, "saloon-root-png")
    trash(SALOON / "_archive", "archive")

    # 6) Temp leftovers
    if TEMP.is_dir():
        for p in TEMP.glob("*"):
            if not p.is_file():
                continue
            n = p.name.lower()
            if any(k in n for k in ("ss0", "bj0", "saloon", "dim_seedvr", "seedvr2_1080")):
                trash(p, "temp")

    print("SUMMARY trashed", len(trashed), "skipped", len(skipped), flush=True)
    print("Game stems:", flush=True)
    for stem in STEMS:
        mp4 = GAME / f"{stem}.mp4"
        webm = GAME / f"{stem}.webm"
        baks = list(GAME.glob(f"{stem}*bak*"))
        print(
            f"  {stem:10} mp4={mp4.is_file()} webm={webm.is_file()} baks={len(baks)}",
            flush=True,
        )
    print("Approved:", flush=True)
    for p in sorted(APPROVED.glob("*")):
        print(f"  {p.name} {p.stat().st_size/1e6:.1f}MB", flush=True)
    print("Ready dirs left:", flush=True)
    for d in sorted([p for p in READY.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        print(" ", d.name, flush=True)
    print("Ready top mp4 left:", flush=True)
    for p in sorted(READY.glob("*.mp4")):
        print(" ", p.name, flush=True)
    return 0 if not skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
