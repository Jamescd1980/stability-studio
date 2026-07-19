#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
media_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm", ".mov", ".mkv"}
out = ROOT / "stability-studio-mcp" / "outputs"
left = [
    p.name
    for p in out.iterdir()
    if p.is_file() and p.suffix.lower() in media_ext
] if out.is_dir() else []
print("media_left", len(left))

pat = re.compile(r"api_key\s*[:=]\s*['\"]([^'\"]{12,})['\"]")
hits = []
for p in ROOT.rglob("*"):
    if not p.is_file() or p.name == "config.yaml":
        continue
    if any(x in p.parts for x in ("outputs", "__pycache__", ".venv", ".git", "node_modules")):
        continue
    if p.suffix.lower() not in {".py", ".yaml", ".yml", ".md", ".json", ".example", ".ps1", ".sh", ".txt"}:
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for m in pat.finditer(text):
        val = m.group(1)
        if val.lower() in {"ollama", "your_key_here", "changeme"} or val.startswith("<"):
            continue
        hits.append(str(p))
print("filled_api_key_files", len(set(hits)))
for h in sorted(set(hits))[:30]:
    print(h)
