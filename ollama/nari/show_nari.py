#!/usr/bin/env python3
"""Dump ollama show JSON for nari-prompt."""
import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/show",
    data=json.dumps({"name": "nari-prompt"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=60) as resp:
    d = json.load(resp)
print("arch", (d.get("details") or {}).get("family"), (d.get("details") or {}).get("families"))
print("params", (d.get("parameters") or "")[:300])
print("template_len", len(d.get("template") or ""))
print("template_head", (d.get("template") or "")[:800])
print("keys", sorted(d.keys()))
mi = d.get("model_info") or {}
for k in sorted(mi):
    if "think" in k.lower() or "render" in k.lower() or "parser" in k.lower() or "family" in k.lower():
        print(k, mi[k])
