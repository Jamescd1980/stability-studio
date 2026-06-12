#!/usr/bin/env python3
"""Quick test Wan2GP MCP startup with fixed subprocess env."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config
from studio.gpu_backend import inspect_gpu_backend
from studio.wan2gp_assets import wan2gp_root
from studio.wan2gp_runner import _start_mcp_server, _wait_for_mcp, resolve_wan2gp_python


def main() -> int:
    cfg = load_config()
    root = wan2gp_root(cfg)
    py = resolve_wan2gp_python(cfg)
    if not py:
        print("no python", file=sys.stderr)
        return 2
    print(f"python={py}", flush=True)
    proc = _start_mcp_server(cfg, py, root)
    print(f"started pid={proc.pid}", flush=True)
    try:
        ok = _wait_for_mcp(cfg, proc)
        status = inspect_gpu_backend(cfg)
        print(json.dumps({"ok": ok, "mcp_running": status["wan2gp"].get("mcp_running")}, indent=2))
        return 0 if ok else 1
    except Exception as exc:
        err = proc.stderr.read() if proc.stderr else ""
        print(f"error: {exc}\nstderr:\n{err[:3000]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
