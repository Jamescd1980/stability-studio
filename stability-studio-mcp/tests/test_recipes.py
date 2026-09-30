"""Batch 8: recipe sidecars for splice tools."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from studio.recipes import read_recipe, recipe_path, write_recipe
from studio.video_splice import (
    concat_video_clips,
    splice_crossfade_loop,
    splice_pingpong,
)
from studio.video_utils import probe_video


def _ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.fixture
def cfg_delivery(tmp_path):
    return {"outputs": {"delivery": str(tmp_path)}, "_root": str(tmp_path)}


def _make_clip(dest: Path, seconds: float = 1.0) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=64x64:rate=16",
        "-t",
        str(seconds),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest


@pytest.mark.skipif(not _ffmpeg_ok(), reason="ffmpeg/ffprobe not on PATH")
def test_concat_recipe_round_trip(cfg_delivery, tmp_path):
    a = _make_clip(tmp_path / "a.mp4")
    b = _make_clip(tmp_path / "b.mp4")
    out = tmp_path / "joined.mp4"
    result = concat_video_clips(cfg_delivery, [str(a), str(b)], output_path=str(out))
    assert result.get("ok") is True
    delivered = Path((result.get("delivered_files") or result.get("saved_files"))[0])
    assert recipe_path(delivered).is_file()
    recipe = read_recipe(delivered)
    assert recipe is not None
    assert recipe["schema"] == "onedesk.recipe"
    assert len(recipe["pieces"]) == 2
    probe = probe_video(delivered)
    assert recipe["frames"] == probe["frame_count"]
    assert recipe["joins_known"] is True
    assert len(recipe["joins"]) == 1


@pytest.mark.skipif(not _ffmpeg_ok(), reason="ffmpeg/ffprobe not on PATH")
def test_pingpong_recipe(cfg_delivery, tmp_path):
    src = _make_clip(tmp_path / "src.mp4")
    result = splice_pingpong(cfg_delivery, str(src), then_forward=True)
    assert result.get("ok") is True
    delivered = Path((result.get("delivered_files") or result.get("saved_files"))[0])
    recipe = read_recipe(delivered)
    assert recipe is not None
    assert len(recipe["pieces"]) == 3
    assert recipe["pieces"][1]["reversed"] is True


@pytest.mark.skipif(not _ffmpeg_ok(), reason="ffmpeg/ffprobe not on PATH")
def test_crossfade_recipe(cfg_delivery, tmp_path):
    src = _make_clip(tmp_path / "src.mp4")
    result = splice_crossfade_loop(cfg_delivery, str(src), fade_sec=0.25)
    assert result.get("ok") is True
    delivered = Path((result.get("delivered_files") or result.get("saved_files"))[0])
    recipe = read_recipe(delivered)
    assert recipe is not None
    assert len(recipe["joins"]) == 1
    assert recipe["joins"][0]["transition"]["type"] == "xfade"


def test_recipe_write_error_keeps_splice_ok(cfg_delivery, tmp_path):
    if not _ffmpeg_ok():
        pytest.skip("ffmpeg/ffprobe not on PATH")
    a = _make_clip(tmp_path / "a.mp4")
    b = _make_clip(tmp_path / "b.mp4")
    with patch("studio.recipes.write_recipe", side_effect=OSError("disk full")):
        result = concat_video_clips(cfg_delivery, [str(a), str(b)])
    assert result.get("ok") is True
    assert "recipe_error" in result
    assert "recipe_files" not in result


def test_read_video_recipe_missing():
    from server import read_video_recipe

    payload = json.loads(read_video_recipe(str(Path("Z:/no_such_clip_abc123.mp4"))))
    assert payload["ok"] is False
    assert "No recipe" in payload["error"]


def test_write_recipe_refuses_wrong_output(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"not really video")
    other = tmp_path / "other.recipe.json"
    other.write_text(json.dumps({"output": "other.mp4", "schema": "onedesk.recipe"}), encoding="utf-8")
    wrong = tmp_path / "clip.recipe.json"
    wrong.write_text(json.dumps({"output": "other.mp4", "schema": "onedesk.recipe"}), encoding="utf-8")
    with pytest.raises(ValueError):
        write_recipe(video, {"schema": "onedesk.recipe", "version": 1, "output": "clip.mp4", "pieces": []})
