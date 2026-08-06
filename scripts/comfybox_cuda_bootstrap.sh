#!/usr/bin/env bash
# Phase 1b bootstrap: stop ROCm ComfyUI, install NVIDIA open driver, purge ROCm.
# Run on LinuxBox as james (uses passwordless sudo). Reboot required after.
set -euo pipefail

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP=/mnt/game/backups/cuda-migration-$STAMP
mkdir -p "$BACKUP"

echo "==> Stopping ComfyUI (ROCm)"
sudo systemctl stop comfyui.service || true
sudo systemctl disable comfyui.service || true

echo "==> Freezing custom_nodes + pip + unit"
ls -1 /home/james/ComfyUI/custom_nodes > "$BACKUP/custom_nodes.txt"
if [[ -x /home/james/ComfyUI/.venv/bin/pip ]]; then
  /home/james/ComfyUI/.venv/bin/pip freeze > "$BACKUP/pip-freeze-rocm.txt" || true
fi
cp -a /etc/systemd/system/comfyui.service "$BACKUP/comfyui.service.rocm" || true
cp -a /home/james/ComfyUI/extra_model_paths.yaml "$BACKUP/" || true
cp -a /home/james/ComfyUI/comfyui-linuxbox.sh "$BACKUP/" || true

echo "==> Archiving ROCm venv (keep models/nodes)"
if [[ -d /home/james/ComfyUI/.venv ]]; then
  mv /home/james/ComfyUI/.venv "$BACKUP/ComfyUI.venv.rocm"
fi

echo "==> Installing NVIDIA driver (ubuntu-drivers recommended: 595-open)"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nvidia-driver-595-open

echo "==> Purging ROCm/HIP packages (keep /opt/rocm dirs until reboot cleanup)"
# Remove ROCm metapackages / hip stack; ignore missing.
sudo DEBIAN_FRONTEND=noninteractive apt-get purge -y 'rocm*' 'hip*' 'hsa-*' 'rocblas*' 'miopen*' 'rccl*' 'rocalution*' 'rocfft*' 'comgr' || true
sudo DEBIAN_FRONTEND=noninteractive apt-get autoremove -y || true

echo "==> Writing CUDA ComfyUI systemd unit (not started until after reboot + venv)"
sudo tee /etc/systemd/system/comfyui.service >/dev/null <<'UNIT'
[Unit]
Description=ComfyUI (CUDA, RTX 5090)
After=network-online.target
Wants=network-online.target
RequiresMountsFor=/mnt/game

[Service]
Type=simple
User=james
Group=james
WorkingDirectory=/home/james/ComfyUI
Environment=CUDA_VISIBLE_DEVICES=0
Environment=VHS_USE_IMAGEIO_FFMPEG=1
Environment=PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ExecStart=/home/james/ComfyUI/.venv/bin/python main.py --listen 0.0.0.0 --port 8188 --output-directory "/mnt/game/ComfyBox Images and Videos/Images" --input-directory /mnt/game/comfyui-input --temp-directory /mnt/game/comfyui-temp
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload

echo "==> Updating launch helper"
cat > /home/james/ComfyUI/comfyui-linuxbox.sh <<'SH'
#!/usr/bin/env bash
# Launch ComfyUI on LinuxBox (RTX 5090 CUDA). Models via extra_model_paths.yaml on /mnt/game.
set -u
export CUDA_VISIBLE_DEVICES=0
export VHS_USE_IMAGEIO_FFMPEG=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

cd ~/ComfyUI || exit 1
exec ./.venv/bin/python main.py \
    --listen 0.0.0.0 --port 8188 \
    --output-directory "/mnt/game/ComfyBox Images and Videos/Images" \
    --input-directory  /mnt/game/comfyui-input \
    --temp-directory   /mnt/game/comfyui-temp \
    "$@"
SH
chmod +x /home/james/ComfyUI/comfyui-linuxbox.sh

echo "==> Backup at $BACKUP"
echo "NEXT: reboot, then run comfybox_cuda_venv.sh"
echo "REBOOT_NOW=1"
