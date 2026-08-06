#!/usr/bin/env bash
set -eu
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
cd /home/james/studio-edge
pkill -f '[s]wayidle' 2>/dev/null || true
swaymsg 'output * power on' 2>/dev/null || true
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
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if grep -q 'Studio Edge ready' /tmp/myra.log 2>/dev/null; then
    echo "ready after ${i}s"
    break
  fi
  sleep 1
done
tail -30 /tmp/myra.log
echo "=== procs ==="
pgrep -af studio_edge.main || echo 'NO PROCESS'
