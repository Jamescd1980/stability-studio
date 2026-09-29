"""Assemble house_pref_IL train set from anti_sprawl + approved keepers.

Covers as many house vices as one concept LoRA can:
- unprompted windows / trees / bright sun / lamp clutter (from anti_sprawl)
- picture-in-picture / panels / collage / multi-frame (from KEEP CGs + captions)
- closed dim rooms / plain walls (BG keepers + anti_sprawl)

Does NOT try to fix: dual-ID bleed, facesitting pose, contact anatomy (need ckpt merge / pose LoRAs).

Trigger: housepref
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

OUT = Path(r"D:\ComfyBox Images and Videos\assets\house_pref_dataset")
PREF = OUT / "preferred"
REJ = OUT / "reject"

ANTI_PREF = Path(
    r"D:\ComfyBox Images and Videos\assets\Darkness\anti_sprawl_dataset\preferred"
)
ANTI_REJ = Path(
    r"D:\ComfyBox Images and Videos\assets\Darkness\anti_sprawl_dataset\reject"
)
APPROVED = Path(r"D:\Bad boy\TheaterJobs\staging\approved")

# Single-frame sex keepers — teach "one full scene, not PIP/panels"
SEX_KEEPS = [
    APPROVED / "cg/Movie_WildFern/FD_kissing_KEEP.png",
    APPROVED / "cg/Movie_WildFern/FD_fern_licks_darkness_KEEP.png",
    APPROVED / "cg/Movie_WildFern/FD_darkness_licks_fern_KEEP.png",
    APPROVED / "cg/Movie_WildFern/FD_fern_strap_darkness_KEEP.png",
    APPROVED / "cg/Movie_WildFern/FD_darkness_strap_fern_KEEP.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_01_kiss.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_02_facesit.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_02_fern_licks.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_03_darkness_licks.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_03_fern_licks.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_04_darkness_strap.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_05_fern_strap.png",
    APPROVED / "cg/Movie_WildFern/Movie_WildFern_06_aftercare.png",
    APPROVED / "cg/Water_Closet/Water_Closet_01.png",
    APPROVED / "cg/Water_Closet/Water_Closet_02.png",
    APPROVED / "cg/Water_Closet/Water_Closet_03.png",
    APPROVED / "cg/Water_Closet/Water_Closet_04.png",
    APPROVED / "cg/Water_Closet/Water_Closet_05.png",
]

# Closed-room / dim BG plates — reinforce no window invent
BG_KEEPS = [
    APPROVED / "bg/fern_room_night.png",
    APPROVED / "bg/frieren_room_night.png",
    APPROVED / "bg/break_room.png",
    APPROVED / "bg/theater_staff_hallway.png",
    APPROVED / "bg/second_floor_hallway.png",
    APPROVED / "bg/medical_ward_night.png",
]

SEX_CAPTION = (
    "housepref, single frame, full scene, no panels, no picture in picture, "
    "no collage, no inset, anime illustration, closed indoor room, "
    "muted dim indoor lighting, soft shadow"
)

BG_CAPTION = (
    "housepref, single frame, empty room, plain wall, closed indoor room, "
    "no window, no picture in picture, no panels, muted dim indoor lighting, "
    "soft shadow, anime illustration"
)


def rewrite_asprawl_caption(old: str) -> str:
    # Keep scene tags; swap trigger + add PIP prefs
    body = old
    for prefix in ("asprawl, ", "sprawl_bad, "):
        if body.startswith(prefix):
            body = body[len(prefix) :]
            break
    return (
        "housepref, single frame, no panels, no picture in picture, no collage, "
        "empty wall, plain wall, closed indoor room, muted dim indoor lighting, "
        "soft shadow, anime illustration, " + body
    )


def main() -> None:
    if PREF.exists():
        shutil.rmtree(PREF)
    if REJ.exists():
        shutil.rmtree(REJ)
    PREF.mkdir(parents=True)
    REJ.mkdir(parents=True)

    manifest: list[dict] = []
    n = 0

    # 1) anti_sprawl preferred → housepref captions
    for img in sorted(ANTI_PREF.glob("*.png")):
        stem = f"asprawl_{img.stem}"
        dst = PREF / f"{stem}.png"
        shutil.copy2(img, dst)
        txt = ANTI_PREF / f"{img.stem}.txt"
        old = txt.read_text(encoding="utf-8") if txt.exists() else "empty wall, plain wall"
        (PREF / f"{stem}.txt").write_text(rewrite_asprawl_caption(old), encoding="utf-8")
        manifest.append({"src": str(img), "dst": str(dst), "kind": "anti_sprawl"})
        n += 1

    # 2) sex keepers
    for img in SEX_KEEPS:
        if not img.exists():
            print("MISSING sex", img)
            continue
        stem = f"sex_{img.stem}"
        dst = PREF / f"{stem}.png"
        shutil.copy2(img, dst)
        (PREF / f"{stem}.txt").write_text(SEX_CAPTION, encoding="utf-8")
        manifest.append({"src": str(img), "dst": str(dst), "kind": "sex_keep"})
        n += 1

    # 3) BG keepers
    for img in BG_KEEPS:
        if not img.exists():
            print("MISSING bg", img)
            continue
        stem = f"bg_{img.stem}"
        dst = PREF / f"{stem}.png"
        shutil.copy2(img, dst)
        (PREF / f"{stem}.txt").write_text(BG_CAPTION, encoding="utf-8")
        manifest.append({"src": str(img), "dst": str(dst), "kind": "bg_keep"})
        n += 1

    # 4) reject eval (not trained) — sprawl + captioned PIP vices
    rn = 0
    for img in sorted(ANTI_REJ.glob("*.png")):
        stem = f"rej_{img.stem}"
        dst = REJ / f"{stem}.png"
        shutil.copy2(img, dst)
        (REJ / f"{stem}.txt").write_text(
            "badpref, picture in picture, panels, collage, bright window, trees, floor lamp",
            encoding="utf-8",
        )
        rn += 1

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "house_pref_IL dataset\n"
        "Trigger: housepref\n"
        "Train folder: preferred/ (Kohya: 10_housepref or 12_housepref)\n"
        "Reject is eval-only — do not train on reject/\n"
        f"preferred={n} reject={rn}\n",
        encoding="utf-8",
    )
    print(f"DONE preferred={n} reject={rn} -> {OUT}")


if __name__ == "__main__":
    main()
