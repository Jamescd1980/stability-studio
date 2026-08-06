"""Promote Wild Fern city/wood keepers → forge_soften + game CGs (pad 1920x1080).

Eyes pass later (mask/fix). Aftercare + 03_darkness_licks unchanged.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from send2trash import send2trash

W, H = 1920, 1080
STILLS = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills"
)
FORGE = STILLS / "forge_soften"
KEEPERS = FORGE / "_bgcity_i2i" / "_keepers"
CG = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_WildFern")

# User-approved denoise picks already copied into _keepers
PROMOTE = [
    # (keeper file, forge_soften name, game cg name)
    ("01_kiss.png", "Movie_WildFern_01_kiss_forge_soften.png", "Movie_WildFern_01_kiss.png"),
    ("02_fern_licks.png", "Movie_WildFern_02_fern_licks_forge_soften.png", "Movie_WildFern_02_fern_licks.png"),
    ("04_fern_revcowgirl.png", "Movie_WildFern_04_fern_revcowgirl_forge_soften.png", "Movie_WildFern_04_fern_revcowgirl.png"),
    ("05_fern_doggy.png", "Movie_WildFern_05_fern_doggy_forge_soften.png", "Movie_WildFern_05_fern_doggy.png"),
]
FACESIT_KEEP = ("facesit_i2i_bghard_d62.png", "facesit_darkness_pov_city_KEEP.png")


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
    canvas.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    if dst.is_file():
        send2trash(str(dst))
    canvas.save(dst, "PNG")
    print(f"  CG {dst.name} plate={fg.size}", flush=True)


def replace_copy(src: Path, dst: Path) -> None:
    if dst.is_file():
        send2trash(str(dst))
    shutil.copy2(src, dst)
    print(f"  forge {dst.name}", flush=True)


def main() -> int:
    CG.mkdir(parents=True, exist_ok=True)
    FORGE.mkdir(parents=True, exist_ok=True)
    print("=== promote Wild Fern city keepers ===", flush=True)
    for keep_name, forge_name, cg_name in PROMOTE:
        src = KEEPERS / keep_name
        if not src.is_file():
            print("MISSING", src, flush=True)
            return 1
        replace_copy(src, FORGE / forge_name)
        pad_blur(src, CG / cg_name)

    fs_src = KEEPERS / FACESIT_KEEP[0]
    if fs_src.is_file():
        replace_copy(fs_src, FORGE / FACESIT_KEEP[1])
    else:
        # already promoted earlier
        print("facesit keeper already at", FORGE / FACESIT_KEEP[1], flush=True)

    print("SKIP Movie_WildFern_03_darkness_licks (no city remake)", flush=True)
    print("SKIP Movie_WildFern_06_aftercare (leave original)", flush=True)
    print("DONE — eyes mask/fix next when you say go", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
