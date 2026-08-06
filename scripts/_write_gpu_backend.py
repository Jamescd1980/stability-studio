from pathlib import Path
import base64

text = """#!/usr/bin/env bash
# Exclusive GPU helpers for LinuxBox (RTX 5090 CUDA).
set -euo pipefail

cmd=\"${1:-status}\"

status() {
  echo \"=== GPU ===\"
  nvidia-smi -L 2>/dev/null || true
  nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
  echo \"=== comfyui ===\"
  systemctl is-active comfyui 2>/dev/null || echo inactive
  echo \"=== blender-mcp ===\"
  ss -ltn | grep 9876 || echo \"port 9876 closed\"
  pgrep -af '/mnt/game/apps/blender/blender' | head -3 || echo none
  echo \"=== forge ===\"
  pgrep -af \"launch.py|webui.sh\" || echo none
}

case \"$cmd\" in
  status) status ;;
  comfy)
    echo \"Stopping Blender MCP / Forge...\"
    pkill -f '/mnt/game/apps/blender/blender' 2>/dev/null || true
    pkill -f \"launch.py\" 2>/dev/null || true
    sleep 2
    sudo systemctl start comfyui
    status
    ;;
  blender)
    echo \"Stopping ComfyUI / Forge for Blender MCP on 5090...\"
    sudo systemctl stop comfyui || true
    pkill -f \"launch.py\" 2>/dev/null || true
    sleep 2
    bash /home/james/bin/comfybox_start_blender_mcp.sh
    status
    ;;
  forge)
    echo \"Stopping ComfyUI / Blender...\"
    sudo systemctl stop comfyui || true
    pkill -f '/mnt/game/apps/blender/blender' 2>/dev/null || true
    sleep 2
    cd /mnt/game/sd-webui-forge
    nohup ./webui.sh > /mnt/game/sd-webui-forge/forge.log 2>&1 &
    echo \"Forge starting\"
    sleep 3
    status
    ;;
  stop-all)
    sudo systemctl stop comfyui || true
    pkill -f \"launch.py\" 2>/dev/null || true
    pkill -f '/mnt/game/apps/blender/blender' 2>/dev/null || true
    status
    ;;
  stop-comfy)
    sudo systemctl stop comfyui || true
    status
    ;;
  *)
    echo \"Usage: $0 {status|comfy|blender|forge|stop-all|stop-comfy}\"
    exit 1
    ;;
esac
"""
p = Path(r"d:\studio-agent\scripts\comfybox_gpu_backend.sh")
data = text.encode("utf-8")
p.write_bytes(data)
Path(r"d:\studio-agent\scripts\_gpu_b64.txt").write_text(base64.b64encode(data).decode("ascii"), encoding="ascii")
print(p.stat().st_size)
