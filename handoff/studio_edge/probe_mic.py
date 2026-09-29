#!/usr/bin/env python3
"""Probe SoloCast levels on Myra."""
import numpy as np
import sounddevice as sd

devs = sd.query_devices()
idx = None
for i, d in enumerate(devs):
    name = str(d.get("name") or "")
    print(f"{i}: {name!r} in={d['max_input_channels']} rate={d['default_samplerate']}")
    if "SoloCast" in name or "HyperX" in name:
        idx = i
print("---")
if idx is None:
    raise SystemExit("NO_SOLOCAST")
ch = min(2, int(devs[idx]["max_input_channels"]))
rec = sd.rec(int(44100 * 1.5), samplerate=44100, channels=ch, dtype="int16", device=idx)
sd.wait()
mono = rec.mean(axis=1) if rec.ndim > 1 else rec.reshape(-1)
peak = int(np.max(np.abs(mono)))
rms = int(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
print("device", idx, "ch", ch, "peak", peak, "rms", rms)
if peak < 50:
    print("HINT: near-silence — mic likely muted or wrong device")
