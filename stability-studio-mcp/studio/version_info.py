"""Package version and build metadata for get_generation_context."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_version() -> str:
    path = ROOT / "VERSION"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return "0.0.0-dev"


def git_revision() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def build_info() -> dict[str, str | None]:
    return {
        "version": read_version(),
        "git_revision": git_revision(),
        "package_root": str(ROOT),
    }
