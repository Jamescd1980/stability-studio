"""Video helpers for V2V extension (frame extract, concat, probe)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_video(path: Path) -> dict[str, float | int]:
    """Return duration_sec, frame_count, fps from ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=nb_frames,r_frame_rate,duration",
        "-of",
        "json",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True)
    data = json.loads(out)
    stream = (data.get("streams") or [{}])[0]
    duration = float(stream.get("duration") or 0)
    fps = 16.0
    rate = stream.get("r_frame_rate", "16/1")
    if "/" in str(rate):
        num, den = str(rate).split("/", 1)
        if float(den):
            fps = float(num) / float(den)
    frame_count = stream.get("nb_frames")
    if frame_count is not None:
        count = int(frame_count)
    elif duration > 0:
        count = max(1, int(round(duration * fps)))
    else:
        count = 1
    return {"duration_sec": duration, "frame_count": count, "fps": fps}


def _extract_frame_index(video: Path, dest: Path, frame_index: int) -> bool:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{frame_index})",
            "-vframes",
            "1",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest.is_file() and dest.stat().st_size > 500


def extract_last_frame(video: Path, dest: Path) -> Path:
    """Extract the last video frame to a PNG; fall back to middle frame if needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            "-0.05",
            "-i",
            str(video),
            "-update",
            "1",
            "-q:v",
            "1",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    if dest.is_file() and dest.stat().st_size > 500:
        return dest

    info = probe_video(video)
    count = max(1, int(info["frame_count"]))
    for idx in (count - 1, count // 2, 0):
        if _extract_frame_index(video, dest, idx):
            return dest
    raise RuntimeError(f"Failed to extract a usable frame from {video}")


def concat_videos(paths: list[Path], dest: Path) -> Path:
    """Concatenate MP4s losslessly (same codec/fps)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    list_file = dest.with_suffix(".txt")
    list_file.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in paths),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest


def comfy_input_dir(cfg: dict) -> Path:
    sm = cfg.get("stability_matrix", {})
    packages = sm.get("packages", {})
    return Path(packages.get("comfyui", "")) / "input"


def copy_to_comfy_input(cfg: dict, path: Path, *, overwrite: bool = True) -> str:
    """Copy a local file into ComfyUI input/; returns filename for LoadImage / VHS_LoadVideo."""
    dest_dir = comfy_input_dir(cfg)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name
    if dest.is_file() and not overwrite:
        return path.name
    dest.write_bytes(path.read_bytes())
    return path.name
