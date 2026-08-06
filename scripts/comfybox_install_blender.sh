#!/usr/bin/env bash
set -euo pipefail
mkdir -p /mnt/game/apps "/mnt/game/ComfyBox Images and Videos/assets/blender/pose" "/mnt/game/ComfyBox Images and Videos/assets/blender/depth" "/mnt/game/ComfyBox Images and Videos/assets/blender/previz" /home/james/.config/blender /home/james/bin
cd /mnt/game/apps
if [[ ! -x /mnt/game/apps/blender/blender ]]; then
  URL="https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz"
  echo "Downloading $URL"
  curl -fL --progress-bar -o blender.tar.xz "$URL"
  rm -rf blender-extract
  mkdir blender-extract
  tar -xJf blender.tar.xz -C blender-extract
  DIR=$(find blender-extract -maxdepth 1 -type d -name 'blender-*' | head -1)
  rm -rf blender
  mv "$DIR" blender
  rm -f blender.tar.xz
  rm -rf blender-extract
fi
/mnt/game/apps/blender/blender --version | head -5
ln -sfn /mnt/game/apps/blender/blender /home/james/bin/blender
mkdir -p /mnt/game/apps/blender-mcp
curl -fsSL -o /mnt/game/apps/blender-mcp/addon.py https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py
VER=$(/mnt/game/apps/blender/blender --version | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
ADDON_DIR="/home/james/.config/blender/${VER}/scripts/addons"
mkdir -p "$ADDON_DIR"
cp -f /mnt/game/apps/blender-mcp/addon.py "$ADDON_DIR/blender_mcp_addon.py"
echo "ADDON_DIR=$ADDON_DIR"
/mnt/game/apps/blender/blender -b --python-expr "import addon_utils,bpy; addon_utils.enable('blender_mcp_addon', default_set=True, persistent=True); bpy.ops.wm.save_userpref(); print('ADDON_ENABLE_DONE')" 2>&1 | tail -40
cat > /home/james/bin/start_blender_mcp.sh << 'SH'
#!/usr/bin/env bash
set -euo pipefail
export CYCLES_DEVICE=CUDA
exec /mnt/game/apps/blender/blender "$@"
SH
chmod +x /home/james/bin/start_blender_mcp.sh
python3 -c "from pathlib import Path; t=Path('/mnt/game/apps/blender-mcp/addon.py').read_text(errors='replace'); print('host_counts', t.count('0.0.0.0'), t.count('127.0.0.1'), t.count('localhost'))"
echo PHASE0_OK
