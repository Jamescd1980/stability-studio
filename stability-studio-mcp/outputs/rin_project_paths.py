"""Deprecated path helpers — use studio.storyboard_cli or generate_storyboard.py."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MCP_ROOT))

from studio.config import load_config  # noqa: E402
from studio.storyboard_cli import paths_for_project, resolve_project_dir  # noqa: E402

warnings.warn(
    "outputs/rin_project_paths.py is deprecated; use generate_storyboard.py --project-dir",
    DeprecationWarning,
    stacklevel=2,
)

_cfg = load_config()
ROOT = resolve_project_dir(None, cfg=_cfg, create=False)
_paths = paths_for_project(ROOT, _cfg)

SOURCE = _paths["source"]
IMAGES = _paths["images"]
CHAIN = _paths["chain"]
ASSETS = _paths["assets"]
CLIPS = _paths["clips"]
AUDIO = _paths["audio"]
TEMP = _paths["temp"]
LOGS = _paths["logs"]
FINAL = _paths["final"]
REJECTED = _paths["rejected"]
SUBDIRS = (SOURCE, IMAGES, CHAIN, ASSETS, CLIPS, AUDIO, TEMP, LOGS, FINAL, REJECTED)


def ensure_layout() -> None:
    resolve_project_dir(None, cfg=_cfg, create=True)


HERO_STILL = IMAGES / "Rin_kitsune_approved.png"
CLIP1_WALK = CLIPS / "Rin_clip1_walk.mp4"
CLIP2_BOW = CLIPS / "Rin_clip2_bow.mp4"
CLIP3_STAB_FADE = CLIPS / "Rin_clip3_stab_fade.mp4"
STORYBOARD_SPLICED = FINAL / "Rin_storyboard_spliced.mp4"
STORYBOARD_SPLICED_ALT = FINAL / "Rin_storyboard_spliced_alt.mp4"
