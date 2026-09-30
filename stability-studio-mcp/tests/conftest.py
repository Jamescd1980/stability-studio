"""Shared test setup: never touch the real Recycle Bin."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def fake_recycle_bin(tmp_path_factory, monkeypatch):
    """Replace recycle_path with a move into a temp "bin" folder; returns the list of recycled paths."""
    bin_dir = tmp_path_factory.mktemp("fake_recycle_bin")
    recycled: list[Path] = []

    def _fake(path: Path) -> bool:
        path = Path(path)
        if not path.exists():
            return False
        shutil.move(str(path), str(bin_dir / f"{uuid.uuid4().hex}_{path.name}"))
        recycled.append(path)
        return True

    import studio.output_paths as output_paths
    import studio.video_splice as video_splice

    monkeypatch.setattr(output_paths, "recycle_path", _fake)
    monkeypatch.setattr(video_splice, "recycle_path", _fake)
    return recycled
