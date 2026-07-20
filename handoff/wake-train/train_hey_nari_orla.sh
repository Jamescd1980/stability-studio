#!/usr/bin/env bash
# Train hey_nari + hey_orla on ComfyBox (same stack as hey_myra / hey_jan).
set -euo pipefail

ROOT=/mnt/game/openwakeword-train/openWakeWord-Trainer
DATA=/mnt/game/openwakeword-train
LOGDIR=$DATA/logs
mkdir -p "$LOGDIR" "$DATA/trained_wake_words"

cd "$ROOT"
chmod +x train_openwakeword.sh scripts/*.py || true

export OWW_PYTHON_BIN=/usr/bin/python3.12
export OWW_FORCE_CPU=1
export OWW_BACKGROUND_HOURS=1
export OWW_NEGATIVE_FEATURES=full
export OWW_DATA_DIR="$DATA"
export OWW_VENV_DIR="$ROOT/.venv"
export OWW_VENDOR_DIR="$DATA/vendor"
export OWW_OUTPUT_ROOT="$DATA/output"
export OWW_EXPORT_DIR="$DATA/trained_wake_words"
export OWW_ASSET_DIR="$DATA/data"
export OWW_OPENWAKEWORD_DIR="$DATA/vendor/openwakeword"
export OWW_PIPER_DIR="$DATA/vendor/piper-sample-generator"

if [[ ! -x "$OWW_VENV_DIR/bin/python" ]]; then
  echo "Missing training venv at $OWW_VENV_DIR"
  echo "Bootstrap deps from train_on_comfybox.sh first."
  exit 1
fi
# shellcheck disable=SC1091
source "$OWW_VENV_DIR/bin/activate"

echo cpu > "$OWW_VENV_DIR/.train_deps_key"
touch "$OWW_VENV_DIR/.train_deps_installed"

echo "=== starting hey_nari ==="
./train_openwakeword.sh "hey nari" \
  --model-name hey_nari \
  --samples 10000 \
  --validation-samples 1200 \
  --steps 20000 \
  --custom-negative-phrase "hey mary" \
  --custom-negative-phrase "hey narry" \
  --custom-negative-phrase "hey nancy" \
  --force-cpu \
  2>&1 | tee "$LOGDIR/train_hey_nari.log"

echo "=== starting hey_orla ==="
./train_openwakeword.sh "hey orla" \
  --model-name hey_orla \
  --samples 10000 \
  --validation-samples 1200 \
  --steps 20000 \
  --custom-negative-phrase "hey oral" \
  --custom-negative-phrase "hey ora" \
  --custom-negative-phrase "hey arla" \
  --force-cpu \
  2>&1 | tee "$LOGDIR/train_hey_orla.log"

echo "=== DONE ==="
ls -la "$DATA/trained_wake_words/hey_nari.onnx" "$DATA/trained_wake_words/hey_orla.onnx"
