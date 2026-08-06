"""Saloon pack: bright masters → SeedVR-only (no RIFE) → fat VP9 WebM in game."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageFilter
from send2trash import send2trash

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.video_post import polish_wan_best  # noqa: E402

READY = Path(
    r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon\Ready for Post Production"
)
OUT = READY / "_bright_seedvr"
GAME_VID = Path(r"D:\Bad boy\TheaterJobs\game\videos\Movie_Saloon")
GAME_CG = Path(r"D:\Bad boy\TheaterJobs\game\images\cg\Movie_Saloon")
W, H = 1920, 1080

# stem -> bright master. BJ01 keeps approved FLF (no SeedVR). SS03_1: raw only (prior SeedVR eye reject).
JOBS: list[tuple[str, Path, bool]] = [
    ("BJ01", READY / "Approved" / "BJ01_wan_flf_bob_samestill_loop3s.mp4", False),
    ("BJ02", READY / "BJ02.mp4", True),
    ("SS01", READY / "SS01_pingpong.mp4", True),
    ("SS02", READY / "SS02_LC01_08s_pingpong_long_4x.mp4", True),
    ("SS03_1", READY / "SS03_1_v2_T1.mp4", False),
    ("SS03_2", READY / "SS03_2_v2_COCK_R1b.mp4", True),
    ("SS03_3_1", READY / "SS03_3_1_loop.mp4", True),
    ("SS03_3_2", READY / "SS03_3_2_loop.mp4", True),
    ("SS04", READY / "SS04_1_v2_T13.mp4", True),
    ("SS04_001", READY / "SS04_001_v3.mp4", True),
    ("SS04_002", READY / "SS04_002_v3.mp4", True),
]


def pad_rgb(im: Image.Image) -> Image.Image:
    im = im.convert("RGB")
    if im.size == (W, H):
        return im
    scale = H / im.height
    nw, nh = int(round(im.width * scale)), H
    body = im.resize((nw, nh), Image.Resampling.LANCZOS)
    bg = im.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(36))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.25)
    canvas = bg.copy()
    canvas.paste(body, ((W - nw) // 2, 0))
    return canvas


def encode_fat_webm(src: Path, webm: Path) -> None:
    """VP9 1920x1080 letterbox, CRF 20 (~commercial bitrate class)."""
    tmp = webm.with_suffix("._tmp.webm")
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    )
    subprocess.check_call(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            vf,
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "20",
            "-row-mt",
            "1",
            "-an",
            str(tmp),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if webm.is_file():
        send2trash(str(webm))
    tmp.replace(webm)


def still_from_video(src: Path, stem: str) -> None:
    """Refresh BJ01-style still from f0 when we have a matching CG stem."""
    cg_name = {
        "BJ01": "BJ01.png",
        "BJ02": "BJ02.png",
        "SS01": "SS01.png",
        "SS02": "SS02.png",
        "SS03_1": "SS03_1.png",
        "SS03_2": "SS03_2.png",
        "SS03_3_1": "SS03_3.png",  # script still plate for 3_1 family
        "SS04": None,  # opaque plate separate
        "SS04_001": "SS04_001.png",
        "SS04_002": "SS04_002.png",
    }.get(stem)
    if not cg_name:
        return
    dest = GAME_CG / cg_name
    frame = OUT / f"_{stem}_f0.png"
    subprocess.check_call(
        ["ffmpeg", "-y", "-i", str(src), "-frames:v", "1", str(frame)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if dest.is_file():
        send2trash(str(dest))
    pad_rgb(Image.open(frame)).save(dest, "PNG")
    frame.unlink(missing_ok=True)
    print("still", dest.name, flush=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    GAME_VID.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    results = []

    for stem, src, do_seedvr in JOBS:
        print("===", stem, flush=True)
        if not src.is_file():
            print("MISSING", src, flush=True)
            results.append({"stem": stem, "ok": False, "error": "missing source"})
            continue

        polished = OUT / f"{stem}_bright_seedvr2_1080.mp4"
        if do_seedvr:
            if polished.is_file() and polished.stat().st_size > 100_000:
                print("reuse", polished.name, flush=True)
                final = polished
            else:
                print("SeedVR-only", src.name, flush=True)
                r = polish_wan_best(
                    cfg,
                    str(src),
                    skip_interpolate=True,
                    seedvr2_resolution=1080,
                    crf=17,
                )
                if not r.get("ok"):
                    print("SeedVR FAIL", r.get("error"), "-> bright raw", flush=True)
                    final = src
                else:
                    files = r.get("saved_files") or []
                    out_path = Path(files[0]) if files else Path(r.get("final") or "")
                    if out_path.is_file():
                        shutil.copy2(out_path, polished)
                        final = polished
                        print("SeedVR ok", polished.name, polished.stat().st_size, flush=True)
                    else:
                        print("SeedVR ok but path unknown", r, flush=True)
                        final = src
        else:
            final = src
            print("no-SeedVR keep", src.name, flush=True)

        mp4 = GAME_VID / f"{stem}.mp4"
        webm = GAME_VID / f"{stem}.webm"
        bak = GAME_VID / f"{stem}.mp4.bak_pre_bright"
        if mp4.is_file() and not bak.is_file():
            shutil.copy2(mp4, bak)
        shutil.copy2(final, mp4)
        encode_fat_webm(mp4, webm)
        if stem in ("BJ01", "BJ02", "SS01", "SS02", "SS03_1", "SS03_2", "SS04_001", "SS04_002"):
            still_from_video(final, stem)
        print(
            "installed",
            stem,
            "mp4",
            mp4.stat().st_size,
            "webm",
            webm.stat().st_size,
            flush=True,
        )
        results.append(
            {
                "stem": stem,
                "ok": True,
                "source": str(src),
                "final": str(final),
                "seedvr": do_seedvr and final.resolve() == polished.resolve() if polished.exists() else False,
                "mp4": mp4.stat().st_size,
                "webm": webm.stat().st_size,
            }
        )

    (OUT / "_bright_install.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(x.get("ok") for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
