#!/usr/bin/env bash
# After reboot + nvidia-smi works: create CUDA venv and reinstall ComfyUI deps + nodes.
set -euo pipefail

cd /home/james/ComfyUI

echo "==> nvidia-smi"
nvidia-smi

echo "==> Creating fresh .venv"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel setuptools

echo "==> Installing PyTorch CUDA 12.8 (Blackwell sm_120)"
# Official cu128 wheels; required for RTX 50-series.
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

python - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda", torch.version.cuda)
print("available", torch.cuda.is_available())
print("device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
assert torch.cuda.is_available(), "CUDA not available in torch"
PY

echo "==> ComfyUI requirements"
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt
fi

echo "==> Custom node requirements (best-effort)"
for req in custom_nodes/*/requirements.txt; do
  [[ -f "$req" ]] || continue
  echo "--- $req ---"
  pip install -r "$req" || echo "WARN: failed $req"
done

# Impact Pack often needs its install script
if [[ -f custom_nodes/ComfyUI-Impact-Pack/install.py ]]; then
  python custom_nodes/ComfyUI-Impact-Pack/install.py || true
fi

deactivate
echo "==> Enabling and starting comfyui.service"
sudo systemctl enable comfyui.service
sudo systemctl restart comfyui.service
sleep 5
systemctl --no-pager --full status comfyui.service | head -40
curl -sS -m 10 http://127.0.0.1:8188/system_stats | head -c 800 || true
echo
echo "DONE"
