#!/usr/bin/env bash
# Restart Myra studio edge. Prefer systemd --user when installed.
set -eu
cd /home/james/studio-edge
stamp=$(date +%H%M%S)
if [ -f /tmp/myra.log ]; then
  mv /tmp/myra.log "/tmp/myra.log.bak-$stamp" || true
fi

# Always clear stray nohup copies (Hailo is single-tenant).
pids=$(pgrep -f 'python .*studio_edge.main' || true)
if [ -n "${pids:-}" ]; then
  echo "Stopping: $pids"
  kill $pids 2>/dev/null || true
  sleep 2
  kill -9 $pids 2>/dev/null || true
  sleep 1
fi

if systemctl --user is-enabled studio-edge.service >/dev/null 2>&1; then
  systemctl --user reset-failed studio-edge.service 2>/dev/null || true
  systemctl --user start studio-edge.service
  echo "started via systemd --user"
else
  nohup /home/james/studio-edge-venv/bin/python -u -m studio_edge.main >>/tmp/myra.log 2>&1 &
  echo "started $! (nohup)"
fi

for i in $(seq 1 25); do
  if grep -q 'Studio Edge ready' /tmp/myra.log 2>/dev/null; then
    echo "ready after ${i}s"
    break
  fi
  sleep 1
done
tail -30 /tmp/myra.log || true
pgrep -af 'studio_edge.main' || echo 'NO PROCESS'
