#!/usr/bin/env python3
"""Run one Wan2GP task via in-process API (subprocess entry for Stability Studio)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "usage: run_wan2gp_hero.py <wan2gp_root> <settings.json> [output_dir]"}))
        return 2
    root = Path(sys.argv[1]).resolve()
    settings_path = Path(sys.argv[2]).resolve()
    output_dir = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None

    sys.path.insert(0, str(root))
    import os

    os.chdir(root)

    from shared.api import init

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    session = init(
        root=root,
        output_dir=output_dir,
        console_output=False,
        console_isatty=False,
    )
    job = session.submit_task(settings)
    result = job.result()
    payload = {
        "success": bool(result.success),
        "generated_files": list(result.generated_files),
        "errors": [{"message": e.message, "stage": e.stage} for e in result.errors],
        "cancelled": bool(result.cancelled),
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
