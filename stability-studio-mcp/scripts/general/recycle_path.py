"""Send files/folders to the Windows Recycle Bin (not permanent delete)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def recycle(path: Path) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    try:
        from send2trash import send2trash  # type: ignore

        send2trash(str(path))
        return not path.exists()
    except Exception:
        pass

    ps = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        "$p = $env:RECYCLE_TARGET; "
        "if (Test-Path -LiteralPath $p -PathType Container) { "
        "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory("
        "$p, 'OnlyErrorDialogs', 'SendToRecycleBin') } "
        "else { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
        "$p, 'OnlyErrorDialogs', 'SendToRecycleBin') }"
    )
    env = os.environ.copy()
    env["RECYCLE_TARGET"] = str(path)
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return r.returncode == 0 and not path.exists()


def main() -> int:
    ok = True
    for raw in sys.argv[1:]:
        p = Path(raw)
        if recycle(p):
            print(f"RECYCLE {p}", flush=True)
        else:
            print(f"FAIL {p}", flush=True)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
