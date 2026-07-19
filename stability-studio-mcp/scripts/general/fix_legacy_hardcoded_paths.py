#!/usr/bin/env python3
"""Replace hardcoded Stability Matrix paths in storyboard/legacy scripts."""

from __future__ import annotations

import re
from pathlib import Path

LEGACY = Path(__file__).resolve().parent / "storyboard" / "legacy"

PY_OLD = re.compile(
    r'Path\(r"D:\\StabilityMatrix-win-x64\\Data\\Packages\\ComfyUI\\venv\\Scripts\\python\.exe"\)'
)
FFMPEG_OLD = re.compile(
    r'Path\(\s*r"D:\\StabilityMatrix-win-x64\\Data\\Packages\\ComfyUI\\venv\\Lib\\site-packages"\s*'
    r'r"\\imageio_ffmpeg\\binaries\\ffmpeg-win-x86_64-v7\.1\.exe"\s*\)',
    re.MULTILINE,
)
FFMPEG_OLD2 = re.compile(
    r'r"D:\\StabilityMatrix-win-x64\\Data\\Packages\\ComfyUI\\venv\\Lib\\site-packages"\s*'
    r'r"\\imageio_ffmpeg\\binaries\\ffmpeg-win-x86_64-v7\.1\.exe"',
    re.MULTILINE,
)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    if "_env import" not in text and (PY_OLD.search(text) or FFMPEG_OLD.search(text) or FFMPEG_OLD2.search(text)):
        # After bootstrap import block
        if "from _env import" not in text:
            text = text.replace(
                "import rin_project_paths as P\n",
                "from _env import comfy_python, imageio_ffmpeg\n\nimport rin_project_paths as P\n",
            )
    text = PY_OLD.sub("comfy_python()", text)
    text = FFMPEG_OLD.sub("imageio_ffmpeg()", text)
    text = FFMPEG_OLD2.sub('str(imageio_ffmpeg())', text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    n = 0
    for py in LEGACY.glob("_run_rin_*.py"):
        if patch_file(py):
            print(f"patched {py.name}")
            n += 1
    print(f"Done: {n} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
