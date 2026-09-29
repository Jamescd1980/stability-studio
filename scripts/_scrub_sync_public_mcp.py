"""Sync private MCP package into public worktree and scrub personal data."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

SRC = Path(r"D:\studio-agent")
DST = Path(r"D:\studio-agent-public-mcp")
MCP_SRC = SRC / "stability-studio-mcp"
MCP_DST = DST / "stability-studio-mcp"

COPY_MCP_FILES = [
    "server.py",
    "catalog.yaml",
    "config.yaml.example",
    "requirements.txt",
    "LESSONS-WAN-I2V.md",
]

COPY_MCP_DIRS = [
    "studio",
    "workflows",
]

COPY_ROOT_DOCS = [
    "AGENTS.md",
    "HARDWARE.md",
    "IMAGE-EDITING.md",
    "MODEL-FAMILIES.md",
    "OPEN-INTERPRETER-INTEGRATION.md",
    "CURSOR-INTEGRATION.md",
    "WAN-ASSETS.md",
    "GITHUB.md",
    "LESSONS-COMFYBOX-CUDA.md",
    "COMFYBOX-FORGE.md",
    "BLENDER-MCP.md",
    "POSE-CONTROL.md",
    "IP-ADAPTER-SETUP.md",
    "PATHS.md",
]

SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "venv",
    "temp",
    "outputs",
    "tools",  # huge local binaries / venvs
    "node_modules",
}

REPLACEMENTS: list[tuple[str, str]] = [
    (r"D:\\Users\\Creel\\", r"D:\\Users\\<you>\\"),
    (r"D:/Users/Creel/", r"D:/Users/<you>/"),
    (r"C:\\Users\\Creel\\", r"C:\\Users\\<you>\\"),
    (r"C:/Users/Creel/", r"C:/Users/<you>/"),
    ("Creel", "<you>"),
    ("james@", "user@"),
    ("/home/james/", "/home/<you>/"),
    ("192.168.50.57", "GENERATION_HOST"),
    ("192.168.50.42", "DESK_HOST"),
    ("192.168.50.230", "EDGE_HOST"),
    ("192.168.50.", "127.0.0."),
    ("ssh Linuxbox", "ssh GENERATION_HOST"),
    ("ssh comfybox", "ssh GENERATION_HOST"),
    ("Linuxbox", "GENERATION_HOST"),
    ("LinuxBox", "GENERATION_HOST"),
    ("comfybox", "generation-host"),
    ("ComfyBox", "GenerationHost"),
    (r"D:\\studio-agent", r"<STUDIO_ROOT>"),
    (r"D:/studio-agent", r"<STUDIO_ROOT>"),
    (r"D:\\Bad boy\\", r"<PROJECT>\\"),
    (r"D:/Bad boy/", r"<PROJECT>/"),
    (r"D:\\CoomfyBox Widget", r"<HEAT_MONITOR_REPO>"),
    (r"D:\\ComfyBox Images and Videos", r"<DELIVERY>"),
    (r"D:/ComfyBox Images and Videos", r"<DELIVERY>"),
    ("/mnt/game/", "<MODELS_MOUNT>/"),
    ("Myra", "EdgeVoice"),
    ("Nari", "CreateBrain"),
    ("Orla", "DeskHost"),
]


def scrub_text(text: str) -> str:
    out = text
    for a, b in REPLACEMENTS:
        out = out.replace(a, b)
    # collapse accidental double replacements
    out = out.replace("CreateBrainCreateBrain", "CreateBrain")
    return out


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    raw = src.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        dst.write_bytes(raw)
        return
    dst.write_text(scrub_text(text), encoding="utf-8", newline="\n")


def copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for p in src.rglob("*"):
        if p.is_dir() or should_skip(p.relative_to(src)):
            continue
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(src).parts):
            continue
        rel = p.relative_to(src)
        copy_file(p, dst / rel)
        n += 1
    return n


def main() -> None:
    assert MCP_SRC.is_dir(), MCP_SRC
    assert DST.is_dir(), DST

    for name in COPY_MCP_FILES:
        s = MCP_SRC / name
        if s.is_file():
            copy_file(s, MCP_DST / name)
            print("file", name)

    for d in COPY_MCP_DIRS:
        s = MCP_SRC / d
        if s.is_dir():
            if (MCP_DST / d).exists():
                shutil.rmtree(MCP_DST / d)
            n = copy_tree(s, MCP_DST / d)
            print("dir", d, n, "files")

    # package README
    if (MCP_SRC / "README.md").is_file():
        copy_file(MCP_SRC / "README.md", MCP_DST / "README.md")

    for name in COPY_ROOT_DOCS:
        s = SRC / name
        if s.is_file():
            copy_file(s, DST / name)
            print("doc", name)

    print("OK scrub sync")


if __name__ == "__main__":
    main()
