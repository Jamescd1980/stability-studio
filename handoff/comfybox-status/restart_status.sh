#!/usr/bin/env bash
set -eu
pkill -f '/home/james/comfybox-status/status_server.py' 2>/dev/null || true
sleep 1
nohup python3 /home/james/comfybox-status/status_server.py --listen 0.0.0.0 --port 7870 \
  >/tmp/comfybox-status.log 2>&1 &
echo "pid $!"
sleep 1
curl -sS -m 3 http://127.0.0.1:7870/health || true
echo
pgrep -af status_server.py || true
