"""Pad-import Das Booty face-pass CGs + promote WF04 revcowgirl keeper into game."""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from send2trash import send2trash

W, H = 1920, 1080
SRC_DIR = Path(r"D:\ComfyBox Images and Videos\User Import\Photo Shoots\Das Booty\_face_pass")
DST_DIR = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\das_booty")
VID = Path(r"D:\ComfyBox Images and Videos\Video\studio_agent_wan22_moe_00186.mp4")
WORK = Path(
    r"D:\ComfyBox Images and Videos\Video\Theater Jobs"
    r"\Where the Wild Fern Moans\Work"
)
GAME_VID = Path(r"D:\Bad boy\TheaterJobs\game\videos\Movie_WildFern\fern_revcowgirl.mp4")


def pad_blur(src: Path, dst: Path) -> None:
    im = Image.open(src).convert("RGB")
    bg = im.copy()
    bg.thumbnail((W * 2, H * 2), Image.Resampling.LANCZOS)
    scale = max(W / bg.width, H / bg.height)
    bw, bh = int(bg.width * scale) + 2, int(bg.height * scale) + 2
    bg = bg.resize((bw, bh), Image.Resampling.LANCZOS)
    left = (bw - W) // 2
    top = (bh - H) // 2
    bg = bg.crop((left, top, left + W, top + H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
    arr = (np.asarray(bg).astype(np.float32) * 0.55).clip(0, 255).astype(np.uint8)
    canvas = Image.fromarray(arr, "RGB")
    fg = im.copy()
    fg.thumbnail((W, H), Image.Resampling.LANCZOS)
    x = (W - fg.width) // 2
    y = (H - fg.height) // 2
    canvas.paste(fg, (x, y))
    if dst.is_file():
        send2trash(str(dst))
    canvas.save(dst, "PNG")
    print(f"OK {dst.name} plate={fg.size}", flush=True)


def main() -> int:
    DST_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(1, 8):
        src = SRC_DIR / f"DB-{i:02d}_face.png"
        dst = DST_DIR / f"das_booty_{i:02d}.png"
        if not src.is_file():
            print("MISSING", src, flush=True)
            return 1
        pad_blur(src, dst)

    WORK.mkdir(parents=True, exist_ok=True)
    keep = WORK / "WF04_fern_revcowgirl_i2v_00186_KEEP.mp4"
    GAME_VID.parent.mkdir(parents=True, exist_ok=True)
    if not VID.is_file():
        print("MISSING video", VID, flush=True)
        return 1
    shutil.copy2(VID, keep)
    if GAME_VID.is_file():
        send2trash(str(GAME_VID))
    shutil.copy2(VID, GAME_VID)
    print("PROMOTED", keep, flush=True)
    print("GAME", GAME_VID, GAME_VID.stat().st_size, flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
