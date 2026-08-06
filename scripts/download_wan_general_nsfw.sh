#!/usr/bin/env bash
set -eu
LORA_DIR=/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora
cd "$LORA_DIR"
download_one() {
  local url="$1" out="$2"
  if [ -f "$out" ] && [ "$(stat -c%s "$out" 2>/dev/null || echo 0)" -gt 100000000 ]; then
    echo "OK present $out ($(du -h "$out" | cut -f1))"
    return 0
  fi
  echo "Downloading $out ..."
  curl -L --fail --retry 3 -C - \
    -H "User-Agent: Mozilla/5.0" \
    -o "${out}.tmp" "$url"
  mv "${out}.tmp" "$out"
  ls -lh "$out"
}
# CubeyAI WAN General NSFW v0.08a HIGH / LOW
download_one "https://civitai.com/api/download/models/2073605?type=Model&format=SafeTensor" "NSFW-22-H-e8.safetensors"
download_one "https://civitai.com/api/download/models/2083303?type=Model&format=SafeTensor" "NSFW-22-L-e8.safetensors"
ls -lh NSFW-22-*.safetensors
