#!/usr/bin/env bash
# Rebuild kohya_ss .venv for CUDA (RTX 5090). Archives ROCm .venv if present.
set -euo pipefail
ROOT=/mnt/game/lora-training/kohya_ss
cd "$ROOT"
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p /mnt/game/backups
if [[ -d .venv ]]; then
  mv .venv "/mnt/game/backups/kohya_ss.venv.prev-$STAMP"
fi
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
if [[ -f requirements_linux.txt ]]; then
  python -m pip install -r requirements_linux.txt || true
elif [[ -f requirements.txt ]]; then
  python -m pip install -r requirements.txt || true
fi
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "ok", torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
assert torch.cuda.is_available()
PY
cat > /mnt/game/lora-training/start_kohya_gui.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd /mnt/game/lora-training/kohya_ss
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# shellcheck disable=SC1091
source .venv/bin/activate
exec ./gui.sh --listen 0.0.0.0 --server_port 7861 --headless --noverify
SH
chmod +x /mnt/game/lora-training/start_kohya_gui.sh
echo KOHYA_CUDA_OK
