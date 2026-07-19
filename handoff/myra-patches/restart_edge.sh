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
stamp=$(date +%H%M%S)
if [ -f /tmp/myra.log ]; then
  mv /tmp/myra.log "/tmp/myra.log.bak-$stamp"
fi
nohup /home/james/studio-edge-venv/bin/python -u -m studio_edge.main >>/tmp/myra.log 2>&1 &
echo "started $!"
for i in $(seq 1 20); do
  if grep -q 'Studio Edge ready' /tmp/myra.log 2>/dev/null; then
    echo "ready after ${i}s"
    break
  fi
  sleep 1
done
tail -20 /tmp/myra.log
pgrep -af 'studio_edge.main' || echo 'NO PROCESS'
