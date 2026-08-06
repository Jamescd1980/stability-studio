#!/usr/bin/env python3
from pathlib import Path

paths = [
    Path("/mnt/game/apps/blender-mcp/addon.py"),
    Path("/home/james/.config/blender/4.5/scripts/addons/blender_mcp_addon.py"),
]
old = "host='localhost'"
new = "host='0.0.0.0'"
for p in paths:
    t = p.read_text(encoding="utf-8")
    if old not in t:
        print(p, "NO_MATCH")
        continue
    p.write_text(t.replace(old, new), encoding="utf-8")
    print(p, "PATCHED")
