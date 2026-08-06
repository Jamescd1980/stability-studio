#!/usr/bin/env python3
from pathlib import Path

p = Path.home() / "studio-edge" / "config.yaml"
t = p.read_text(encoding="utf-8")
t = t.replace('input_device: "plughw:2,0"', 'input_device: "hw:2,0"')
if "threshold: 0.35" not in t:
    t = t.replace("threshold: 0.5", "threshold: 0.35", 1)
p.write_text(t, encoding="utf-8")
for ln in p.read_text(encoding="utf-8").splitlines():
    if "input_device" in ln or ln.strip().startswith("threshold:"):
        print(ln)
