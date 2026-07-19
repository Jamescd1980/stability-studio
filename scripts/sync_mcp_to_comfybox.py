#!/usr/bin/env python3
"""One-way sync Windows MCP -> ComfyBox. Windows is source of truth."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(r"D:\studio-agent\stability-studio-mcp")
HOST = "comfybox"
DEST = "/mnt/game/studio-agent/stability-studio-mcp"
ITEMS = [
    "studio",
    "workflows",
    "scripts",
    "catalog.yaml",
    "server.py",
    "requirements.txt",
    "README.md",
    "LESSONS-WAN-I2V.md",
    "config.yaml.example",
]


def main() -> int:
    if not SRC.is_dir():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    items = [i for i in ITEMS if (SRC / i).exists()]
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(SRC.parent), "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        sha = "unknown"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"Sync {SRC} -> {HOST}:{DEST}")
    print("Items:", ", ".join(items))
    subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, f"mkdir -p {DEST}"], check=True)
    cmd = [
        "tar",
        "-cf",
        "-",
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.venv",
        "--exclude=outputs",
        "-C",
        str(SRC),
        *items,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert proc.stdout is not None
    ssh = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", HOST, f"tar -xf - -C {DEST}"],
        stdin=proc.stdout,
    )
    proc.stdout.close()
    rc_ssh = ssh.wait()
    rc_tar = proc.wait()
    if rc_ssh or rc_tar:
        print(f"sync failed tar={rc_tar} ssh={rc_ssh}", file=sys.stderr)
        return 1
    note = (
        "Windows is the source of truth for stability-studio-mcp.\n"
        f"Synced: {stamp}\n"
        f"Git SHA: {sha}\n"
        f"Host path: {SRC}\n"
        "Do not edit catalog/code only on ComfyBox — edit on Windows, "
        "then re-run scripts/sync_mcp_to_comfybox.py\n"
    )
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HOST, f"cat > {DEST}/SYNCED_FROM_WINDOWS.txt"],
        input=note.encode(),
        check=True,
    )
    out = subprocess.check_output(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            HOST,
            f"wc -l {DEST}/catalog.yaml; "
            f"test -f {DEST}/studio/character_loras.py && echo character_loras=ok; "
            f"test -d {DEST}/scripts/nsfw && echo nsfw_scripts=ok; "
            f"head -4 {DEST}/SYNCED_FROM_WINDOWS.txt",
        ],
        text=True,
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
