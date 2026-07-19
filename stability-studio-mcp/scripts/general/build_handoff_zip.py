#!/usr/bin/env python3
"""Build studio-agent.zip for handoff (excludes secrets, personal paths, and local run artifacts)."""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = REPO / "studio-agent.zip"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".cursor/projects",
    "unsloth_compiled_cache",
    ".handoff-extract",
}
SKIP_PREFIXES = (
    "stability-studio-mcp/scripts/dev/",
    "stability-studio-mcp/scripts/storyboard/legacy/",
)
SKIP_REL_FILES = {
    "stability-studio-mcp/scripts/copy_rin_examples.py",
}
SKIP_FILES = {
    "config.yaml",
    "config.generated.yaml",
    "studio-agent.zip",
    "wan_video_loras_local.py",
    "mcp.json",
    "wan_assets_check.txt",
    "wan_loras_check.txt",
    "lora_check.txt",
    "downloads_list.txt",
}
SKIP_EXT = {
    ".pyc",
    ".pyo",
    ".mp4",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".log",
    ".err",
}
# Under stability-studio-mcp/outputs — only ship the placeholder readme + gitkeep.
OUTPUTS_ALLOW = {".gitkeep", "README.md"}


def should_skip(path: Path) -> bool:
    rel_posix = path.relative_to(REPO).as_posix()
    if rel_posix in SKIP_REL_FILES:
        return True
    if any(rel_posix.startswith(p) for p in SKIP_PREFIXES):
        return True
    if path.name in SKIP_FILES:
        return True
    if path.suffix.lower() in SKIP_EXT:
        return True
    parts = path.parts
    if set(parts) & SKIP_DIRS:
        return True
    if "stability-studio-mcp" in parts and "outputs" in parts:
        rel = path.relative_to(REPO / "stability-studio-mcp" / "outputs")
        if rel.parts and rel.parts[0] not in OUTPUTS_ALLOW and str(rel) not in OUTPUTS_ALLOW:
            return True
    if ".cursor" in parts and path.name in ("mcp.json", "mcp.json.local"):
        return True
    if "scripts" in parts and "fix_legacy_hardcoded_paths.py" in parts:
        return True
    # Personal one-off run scripts and session logs stay local.
    if "outputs" in parts and path.name.startswith("_run_"):
        return True
    if "outputs" in parts and "local" in parts:
        return True
    return False


def main() -> None:
    if OUT.is_file():
        OUT.unlink()
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(REPO.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(REPO)
            if should_skip(f):
                continue
            zf.write(f, rel.as_posix())
            count += 1
    size_mb = OUT.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUT} ({count} files, {size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
