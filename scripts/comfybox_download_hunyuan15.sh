#!/usr/bin/env bash
# Download HunyuanVideo 1.5 Comfy-Org repackaged weights onto Game drive.
set -euo pipefail
BASE=/mnt/game/StabilityMatrix-win-x64/Data/Models
PY=/home/james/ComfyUI/.venv/bin/python
REPO=Comfy-Org/HunyuanVideo_1.5_repackaged

"$PY" -m pip install -q -U huggingface_hub

download() {
  local sub="$1" file="$2" dest_dir="$3"
  mkdir -p "$dest_dir"
  if [[ -f "$dest_dir/$file" ]]; then
    echo "OK exists: $dest_dir/$file"
    return 0
  fi
  echo "GET $file -> $dest_dir"
  "$PY" - <<PY
from huggingface_hub import hf_hub_download
import shutil
from pathlib import Path
p = hf_hub_download(repo_id="$REPO", filename="split_files/$sub/$file", local_dir="/mnt/game/comfyui-temp/hf_hunyuan")
dest = Path("$dest_dir") / "$file"
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(p, dest)
print("saved", dest, dest.stat().st_size)
PY
}

# Shared
download text_encoders qwen_2.5_vl_7b_fp8_scaled.safetensors "$BASE/TextEncoders"
download text_encoders byt5_small_glyphxl_fp16.safetensors "$BASE/TextEncoders"
download vae hunyuanvideo15_vae_fp16.safetensors "$BASE/VAE"

# Prefer FP8 distilled for VRAM/speed on 32GB; keep quality variants optional later
download diffusion_models hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.safetensors "$BASE/DiffusionModels"
download diffusion_models hunyuanvideo1.5_720p_t2v_fp16.safetensors "$BASE/DiffusionModels"
download diffusion_models hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.safetensors "$BASE/DiffusionModels"

echo HUNYUAN_DOWNLOAD_OK
ls -lh "$BASE/DiffusionModels"/hunyuanvideo1.5* "$BASE/VAE"/hunyuanvideo15* "$BASE/TextEncoders"/qwen_2.5_vl_7b_fp8_scaled.safetensors "$BASE/TextEncoders"/byt5_small_glyphxl_fp16.safetensors 2>/dev/null || true
