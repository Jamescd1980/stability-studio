#!/usr/bin/env bash
set -euo pipefail
cd /mnt/game/apps
if [[ -x blender/blender-4.5.3-linux-x64/blender ]]; then
  rm -rf /mnt/game/apps/blender-4.5.3-linux-x64
  mv blender/blender-4.5.3-linux-x64 /mnt/game/apps/blender-4.5.3-linux-x64
  rm -rf blender
fi
if [[ -x /mnt/game/apps/blender-4.5.3-linux-x64/blender ]]; then
  ln -sfn /mnt/game/apps/blender-4.5.3-linux-x64 /mnt/game/apps/blender
fi
ls -la /mnt/game/apps/blender/blender
/mnt/game/apps/blender/blender --version | head -5
ln -sfn /mnt/game/apps/blender/blender /home/james/bin/blender
mkdir -p /mnt/game/apps/blender-mcp
curl -fsSL -o /mnt/game/apps/blender-mcp/addon.py https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py
VER=$(/mnt/game/apps/blender/blender --version | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
ADDON_DIR=/home/james/.config/blender/${VER}/scripts/addons
mkdir -p "$ADDON_DIR"
cp -f /mnt/game/apps/blender-mcp/addon.py "$ADDON_DIR/blender_mcp_addon.py"
echo "ADDON_DIR=$ADDON_DIR"
/mnt/game/apps/blender/blender -b --python-expr "import addon_utils,bpy; addon_utils.enable('blender_mcp_addon', default_set=True, persistent=True); bpy.ops.wm.save_userpref(); print('ADDON_ENABLE_DONE')" 2>&1 | tail -40
printf '%s\n' '#!/usr/bin/env bash' 'set -euo pipefail' 'export CYCLES_DEVICE=CUDA' 'exec /mnt/game/apps/blender/blender "$@"' > /home/james/bin/start_blender_mcp.sh
chmod +x /home/james/bin/start_blender_mcp.sh
mkdir -p "/mnt/game/ComfyBox Images and Videos/assets/blender/pose" "/mnt/game/ComfyBox Images and Videos/assets/blender/depth" "/mnt/game/ComfyBox Images and Videos/assets/blender/previz"
python3 -c "t=open('/mnt/game/apps/blender-mcp/addon.py',encoding='utf-8',errors='replace').read(); print('127', t.count('127.0.0.1'), '0000', t.count('0.0.0.0'))"
echo PHASE0_OK
