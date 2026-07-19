#!/usr/bin/env bash
set -eu
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
cd /home/james/studio-edge

# Wake panel / kill screensaver idle
pkill -f '[s]wayidle' 2>/dev/null || true
if command -v swaymsg >/dev/null 2>&1; then
  swaymsg 'output * power on' 2>/dev/null || true
fi
# Use Myra's own wake helper if importable
/home/james/studio-edge-venv/bin/python - <<'PY' || true
from studio_edge.config import load_config
from studio_edge import display
cfg = load_config()
print(display.disable_screensaver(cfg))
PY

# Restart voice loop
pids=$(pgrep -f 'python -u -m studio_edge.main' || true)
if [ -n "${pids:-}" ]; then
  echo "Stopping: $pids"
  kill $pids 2>/dev/null || true
  sleep 2
  kill -9 $pids 2>/dev/null || true
  sleep 1
fi

stamp=$(date +%H%M%S)
if [ -f /tmp/myra.log ]; then
  mv /tmp/myra.log "/tmp/myra.log.bak-$stamp"
fi

nohup /home/james/studio-edge-venv/bin/python -u -m studio_edge.main >>/tmp/myra.log 2>&1 &
echo "started $!"
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if grep -q 'Studio Edge ready' /tmp/myra.log 2>/dev/null; then
    echo "ready after ${i}s"
    break
  fi
  sleep 1
done
tail -25 /tmp/myra.log
echo "=== procs ==="
pgrep -af studio_edge.main || echo 'NO PROCESS'
echo "=== mic ==="
arecord -l
