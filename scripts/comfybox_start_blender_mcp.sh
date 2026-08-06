#!/usr/bin/env bash
# Start Blender on LinuxBox with MCP server auto-started (virtual display).
# Prefer stopping ComfyUI first: ~/bin/gpu_backend.sh stop-comfy (or systemctl stop comfyui)
set -euo pipefail
export CYCLES_DEVICE=CUDA
export DISPLAY="${DISPLAY:-:99}"

mkdir -p /tmp/blender-mcp
STARTUP=/tmp/blender-mcp/auto_start_mcp.py
cat > "$STARTUP" << 'PY'
import bpy
import time

def _start():
    scene = bpy.context.scene
    scene.blendermcp_port = 9876
    scene.blendermcp_auto_start_server = True
    try:
        bpy.ops.blendermcp.start_server()
        print("BlenderMCP: start_server OK on 0.0.0.0:9876")
    except Exception as e:
        print("BlenderMCP: start_server failed:", e)

# Delay until addons fully loaded
bpy.app.timers.register(_start, first_interval=1.0)
print("BlenderMCP: auto-start timer registered")
PY

# Kill stale Blender MCP if needed
pkill -f '/mnt/game/apps/blender/blender' 2>/dev/null || true
sleep 1

nohup xvfb-run -a -s "-screen 0 1920x1080x24" \
  /mnt/game/apps/blender/blender \
  --python "$STARTUP" \
  > /tmp/blender-mcp/blender.log 2>&1 &
echo "PID=$!"
sleep 4
ss -ltn | grep 9876 || true
tail -30 /tmp/blender-mcp/blender.log || true
echo STARTED
