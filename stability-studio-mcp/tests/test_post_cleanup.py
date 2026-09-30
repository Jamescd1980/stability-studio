"""Batch 10: pose worker path, promote_file recycles, ping pong work folder."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from studio import output_paths
from studio.output_paths import promote_file
from studio.video_splice import pose_worker_path, splice_pingpong


def _ffmpeg_ok() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_pose_worker_prefers_general_path(tmp_path):
    new = tmp_path / "scripts" / "general" / "local_post" / "pose_match_loop.py"
    old = tmp_path / "scripts" / "local_post" / "pose_match_loop.py"
    for p in (new, old):
        p.parent.mkdir(parents=True)
        p.write_text("# worker", encoding="utf-8")
    assert pose_worker_path(tmp_path) == new


def test_pose_worker_falls_back_to_legacy(tmp_path):
    old = tmp_path / "scripts" / "local_post" / "pose_match_loop.py"
    old.parent.mkdir(parents=True)
    old.write_text("# worker", encoding="utf-8")
    assert pose_worker_path(tmp_path) == old


def test_pose_worker_missing_names_both(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        pose_worker_path(tmp_path)
    assert "general" in str(exc.value) and "local_post" in str(exc.value)


def test_pose_worker_exists_in_repo():
    assert pose_worker_path().is_file()


def test_promote_file_recycles_existing_dest(tmp_path, fake_recycle_bin):
    src = tmp_path / "new.mp4"
    dest = tmp_path / "keep" / "clip.mp4"
    src.write_bytes(b"new")
    dest.parent.mkdir()
    dest.write_bytes(b"old")
    promote_file(src, dest)
    assert dest.read_bytes() == b"new"
    assert not src.exists()
    assert fake_recycle_bin == [dest]


def test_promote_file_copy_recycles_existing_dest(tmp_path, fake_recycle_bin):
    src = tmp_path / "new.mp4"
    dest = tmp_path / "clip.mp4"
    src.write_bytes(b"new")
    dest.write_bytes(b"old")
    promote_file(src, dest, move=False)
    assert dest.read_bytes() == b"new"
    assert src.exists()
    assert fake_recycle_bin == [dest]


def test_promote_file_refuses_when_recycle_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(output_paths, "recycle_path", lambda p: False)
    src = tmp_path / "new.mp4"
    dest = tmp_path / "clip.mp4"
    src.write_bytes(b"new")
    dest.write_bytes(b"old")
    with pytest.raises(OSError):
        promote_file(src, dest)
    assert dest.read_bytes() == b"old"
    assert src.exists()


@pytest.mark.skipif(not _ffmpeg_ok(), reason="ffmpeg/ffprobe not on PATH")
def test_pingpong_recycles_work_folder(tmp_path, fake_recycle_bin):
    src = tmp_path / "src.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=16",
            "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(src),
        ],
        check=True,
        capture_output=True,
    )
    cfg = {"outputs": {"delivery": str(tmp_path / "delivery")}, "_root": str(tmp_path)}
    result = splice_pingpong(cfg, str(src))
    work = tmp_path / "_src_pingpong_work"
    assert result["ok"] is True
    assert not work.exists()
    assert work in fake_recycle_bin
    assert "work_dir_left" not in result
