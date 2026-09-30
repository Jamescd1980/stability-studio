"""Sidecar .recipe.json files for spliced video outputs."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from studio.video_utils import probe_video


def recipe_path(video: Path | str) -> Path:
    p = Path(video).expanduser().resolve()
    return p.with_name(f"{p.stem}.recipe.json")


def read_recipe(video_path: Path | str) -> dict[str, Any] | None:
    rp = recipe_path(video_path)
    if not rp.is_file():
        return None
    try:
        data = json.loads(rp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _probe_wh(path: Path) -> tuple[int, int]:
    import subprocess

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True)
    stream = (json.loads(out).get("streams") or [{}])[0]
    return int(stream.get("width") or 0), int(stream.get("height") or 0)


def write_recipe(video_path: Path | str, recipe: dict[str, Any]) -> Path:
    """Atomic write; refuse to replace a recipe belonging to another output file."""
    video = Path(video_path).expanduser().resolve()
    dest = recipe_path(video)
    out_name = recipe.get("output") or video.name
    if dest.is_file():
        existing = read_recipe(video)
        if existing and existing.get("output") not in (None, "", video.name, out_name):
            raise ValueError(f"Recipe at {dest} belongs to another clip ({existing.get('output')})")
    payload = {**recipe, "output": video.name}
    fd, tmp = tempfile.mkstemp(prefix=f".{dest.stem}.", suffix=".tmp", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dest)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return dest


def _piece(source: str, in_frame: int, out_frame: int, *, reversed: bool = False) -> dict[str, Any]:
    return {
        "source": str(Path(source).expanduser().resolve()),
        "in_frame": int(in_frame),
        "out_frame": int(out_frame),
        "reversed": bool(reversed),
    }


def _joins_between_pieces(pieces: list[dict[str, Any]], fps: float) -> list[dict[str, Any]]:
    joins: list[dict[str, Any]] = []
    cum = 0
    for i, p in enumerate(pieces):
        span = int(p["out_frame"]) - int(p["in_frame"]) + 1
        cum += span
        if i >= len(pieces) - 1:
            break
        frame = cum
        joins.append(
            {
                "frame": frame,
                "sec": round(frame / fps, 4) if fps else 0.0,
                "transition": None,
            }
        )
    return joins


def base_recipe(
    video: Path,
    *,
    tool: str,
    pieces: list[dict[str, Any]],
    joins: list[dict[str, Any]] | None = None,
    joins_known: bool = True,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    probe = probe_video(video)
    w, h = _probe_wh(video)
    fps = float(probe["fps"])
    frames = int(probe["frame_count"])
    duration = float(probe["duration_sec"])
    if joins is None:
        joins = _joins_between_pieces(pieces, fps)
    return {
        "schema": "onedesk.recipe",
        "version": 1,
        "output": video.name,
        "made_by": {
            "tool": tool,
            "by": "mcp",
            "at": datetime.now(timezone.utc).isoformat(),
        },
        "fps": fps,
        "frames": frames,
        "duration_sec": duration,
        "width": w,
        "height": h,
        "pieces": pieces,
        "joins": joins,
        "joins_known": joins_known,
        "audio_lines": [],
        "params": params or {},
    }


def recipe_for_concat(sources: list[Path], output: Path) -> dict[str, Any]:
    pieces: list[dict[str, Any]] = []
    for src in sources:
        info = probe_video(src)
        last = max(0, int(info["frame_count"]) - 1)
        pieces.append(_piece(str(src), 0, last, reversed=False))
    return base_recipe(output, tool="concat_video_clips", pieces=pieces)


def recipe_for_pingpong(source: Path, output: Path, *, then_forward: bool) -> dict[str, Any]:
    info = probe_video(source)
    last = max(0, int(info["frame_count"]) - 1)
    src = str(source)
    pieces = [
        _piece(src, 0, last, reversed=False),
        _piece(src, 0, last, reversed=True),
    ]
    if then_forward:
        pieces.append(_piece(src, 0, last, reversed=False))
    return base_recipe(output, tool="splice_pingpong", pieces=pieces, params={"then_forward": then_forward})


def recipe_for_crossfade(source: Path, output: Path, fade_sec: float) -> dict[str, Any]:
    info = probe_video(source)
    last = max(0, int(info["frame_count"]) - 1)
    fps = float(info["fps"])
    dur = float(info["duration_sec"])
    fade = max(0.05, min(float(fade_sec), dur / 3))
    offset = max(0.01, dur - fade)
    join_frame = max(1, int(round(offset * fps)))
    src = str(source)
    pieces = [
        _piece(src, 0, last, reversed=False),
        _piece(src, 0, last, reversed=False),
    ]
    joins = [
        {
            "frame": join_frame,
            "sec": round(offset, 4),
            "transition": {"type": "xfade", "sec": fade},
        }
    ]
    return base_recipe(
        output,
        tool="splice_crossfade_loop",
        pieces=pieces,
        joins=joins,
        params={"fade_sec": fade},
    )


def recipe_for_pose_matched(source: Path, output: Path, worker_payload: dict[str, Any]) -> dict[str, Any]:
    params = {
        k: worker_payload[k]
        for k in (
            "target_sec",
            "rewind_max",
            "start_frame",
            "end_frame",
            "half_frame",
            "rewind_frames",
            "match_mse",
            "parts",
        )
        if k in worker_payload
    }
    joins_known = False
    joins: list[dict[str, Any]] = []
    if worker_payload.get("start_frame") is not None and worker_payload.get("end_frame") is not None:
        info = probe_video(source)
        fps = float(info["fps"])
        half = int(worker_payload.get("half_frame") or info["frame_count"] // 2)
        joins = [
            {
                "frame": half,
                "sec": round(half / fps, 4) if fps else 0.0,
                "transition": None,
            }
        ]
        joins_known = True
    info = probe_video(source)
    last = max(0, int(info["frame_count"]) - 1)
    pieces = [_piece(str(source), 0, last, reversed=False)]
    return base_recipe(
        output,
        tool="splice_pose_matched_loop",
        pieces=pieces,
        joins=joins,
        joins_known=joins_known,
        params=params,
    )


def attach_recipes_to_result(
    result: dict[str, Any],
    *,
    tool: str,
    build_for_output: Any,
) -> dict[str, Any]:
    """Never fail the splice if recipe write fails."""
    try:
        outputs = list(result.get("delivered_files") or result.get("saved_files") or [])
        recipe_files: list[str] = []
        for out in outputs:
            path = Path(out).expanduser().resolve()
            if not path.is_file():
                continue
            recipe = build_for_output(path)
            rp = write_recipe(path, recipe)
            recipe_files.append(str(rp))
        if recipe_files:
            result["recipe_files"] = recipe_files
    except Exception as exc:
        result["recipe_error"] = str(exc)
    return result
