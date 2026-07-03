#!/usr/bin/env python3
"""Stability Matrix entry shim — adds --listen for laptop LAN MCP.

Installed to ComfyUI package dir by install_comfyui_lan_launcher.ps1.

Do NOT add --listen in Stability Matrix Extra Launch Arguments (SM passes
"-- listen" with a space and ComfyUI rejects it).
"""
from __future__ import annotations

import os
import subprocess
import sys

_COMFY_DIR = os.path.dirname(os.path.abspath(__file__))
_MAIN = os.path.join(_COMFY_DIR, "main.py")


def _is_broken_listen(token: str) -> bool:
    t = token.strip()
    if t == "-- listen":
        return True
    if t.replace(" ", "") == "--listen" and t != "--listen":
        return True
    return t == "listen"


def _sanitize_launch_args(argv: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if _is_broken_listen(a):
            i += 1
            continue
        if a == "--listen" and i + 1 < len(argv) and _is_broken_listen(argv[i + 1]):
            i += 2
            continue
        if a == "--listen" and i + 1 < len(argv) and argv[i + 1] in {"", "listen"}:
            i += 2
            continue
        if a.startswith("--listen=") and a.split("=", 1)[-1].strip() in {"", "listen"}:
            i += 1
            continue
        if a == "--listen":
            out.append(a)
            i += 1
            continue
        if a == "--port" and i + 1 < len(argv) and argv[i + 1] == "":
            i += 2
            continue
        out.append(a)
        i += 1
    if not any(x == "--listen" or x.startswith("--listen=") for x in out):
        out.append("--listen")
    return out


def main() -> int:
    forwarded = _sanitize_launch_args(list(sys.argv[1:]))
    cmd = [sys.executable, "-u", _MAIN, *forwarded]
    env = os.environ.copy()
    env.setdefault("VHS_USE_IMAGEIO_FFMPEG", "1")
    return subprocess.call(cmd, cwd=_COMFY_DIR, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
