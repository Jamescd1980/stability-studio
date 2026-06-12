"""Shared import bootstrap for legacy per-beat storyboard runners."""

from __future__ import annotations

import sys
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parents[3]
STORYBOARD_ROOT = Path(__file__).resolve().parents[1]


def setup_paths() -> Path:
    outputs = MCP_ROOT / "outputs"
    local = outputs / "local"
    for p in (MCP_ROOT, STORYBOARD_ROOT, outputs, local):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
    return MCP_ROOT
