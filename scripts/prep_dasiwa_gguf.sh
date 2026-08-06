#!/usr/bin/env bash
set -eu
SM=/mnt/game/StabilityMatrix-win-x64/Data/Models
mkdir -p "$SM/DiffusionModels/I2V"
for f in DasiwaWAN22I2V14BTastysinV8_q8High.gguf DasiwaWAN22I2V14BTastysinV8_q8Low.gguf; do
  src="$SM/StableDiffusion/$f"
  dst="$SM/DiffusionModels/I2V/$f"
  if [ -f "$src" ]; then
    ln -sfn "$src" "$dst"
    echo "linked $dst -> $src"
  fi
done
ls -la "$SM/DiffusionModels/I2V/"*Tasty* || true
# show whether GGUF custom node imports
cd /mnt/game/StabilityMatrix-win-x64/Data/Packages/ComfyUI
/mnt/game/StabilityMatrix-win-x64/Data/Packages/ComfyUI/.venv/bin/python - <<'PY' 2>&1 | tail -40
import sys
sys.path.insert(0,'.')
try:
  import custom_nodes.ComfyUI_GGUF as m
except Exception:
  try:
    import importlib
    m = importlib.import_module('custom_nodes.ComfyUI-GGUF')
  except Exception as e:
    print('import fail', e)
    sys.exit(0)
print('mod', m)
PY
