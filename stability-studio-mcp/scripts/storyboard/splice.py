"""Re-export storyboard splice helpers (implementation: studio.storyboard_cli)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from studio.storyboard_cli import run_splice, splice_from_manifest  # noqa: F401


def run_splice_cli(
    project_root: Path,
    manifest_path: Path,
    *,
    cfg=None,
    skip_missing: bool = False,
) -> int:
    code, payload = run_splice(
        project_dir=project_root,
        manifest_name=manifest_path.name,
        skip_missing=skip_missing,
    )
    stream = sys.stdout if code == 0 else sys.stderr
    print(json.dumps(payload, indent=2), file=stream)
    return code
