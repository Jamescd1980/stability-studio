#!/usr/bin/env bash
set -eu
cd /home/james/studio-edge
pids=$(pgrep -f 'python -u -m studio_edge.main' || true)
if [ -n "${pids:-}" ]; then
  echo "Stopping: $pids"
  kill $pids 2>/dev/null || true
  sleep 2
  kill -9 $pids 2>/dev/null || true
  sleep 1
fi

echo "Mic capture test (2s)..."
arecord -D hw:2,0 -f S16_LE -r 48000 -c 1 -d 2 /tmp/mic_test.wav
python3 - <<'PY'
import wave
from pathlib import Path
import array
import math
p = Path("/tmp/mic_test.wav")
w = wave.open(str(p), "rb")
frames = w.readframes(w.getnframes())
w.close()
samples = array.array("h")
samples.frombytes(frames)
if not samples:
    print("EMPTY mic buffer")
    raise SystemExit(2)
mean_sq = sum(float(s) * float(s) for s in samples) / len(samples)
rms = math.sqrt(mean_sq)
peak = max(abs(s) for s in samples)
print(f"rms={rms:.1f} peak={peak} frames={len(samples)}")
if peak < 50:
    print("WARN: mic nearly silent — check USB SoloCast mute/gain")
PY

# Slightly more sensitive wake while debugging dead-mic feel
python3 - <<'PY'
from pathlib import Path
p = Path.home() / "studio-edge" / "config.yaml"
text = p.read_text(encoding="utf-8")
text2 = text.replace("threshold: 0.5", "threshold: 0.35", 1)
if text2 == text and "threshold: 0.35" not in text:
    print("threshold line unchanged; check config manually")
else:
    p.write_text(text2, encoding="utf-8")
    print("wake threshold set to 0.35 (was 0.5 if present)")
for ln in p.read_text(encoding="utf-8").splitlines():
    if "threshold" in ln:
        print(" ", ln.strip())
PY

bash /home/james/studio-edge/restart_edge.sh
echo "Try: Hey Myra"
