#!/usr/bin/env bash
set -eu
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
cd /home/james/studio-edge
/home/james/studio-edge-venv/bin/python - <<'PY'
from studio_edge.config import load_config
from studio_edge import display
cfg = load_config()
print(display.show_comfybox_status(cfg))
PY
