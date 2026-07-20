#!/usr/bin/env bash
# Copy trained hey_nari / hey_orla ONNX to Pi and drop hey_jan.
set -euo pipefail
SRC=/mnt/game/openwakeword-train/trained_wake_words
for m in hey_nari.onnx hey_orla.onnx; do
  [[ -f "$SRC/$m" ]] || { echo "Missing $SRC/$m — train first."; exit 1; }
done
scp "$SRC/hey_nari.onnx" "$SRC/hey_orla.onnx" myra:~/openwakeword-models/
ssh myra 'rm -f ~/openwakeword-models/hey_jan.onnx; ls -la ~/openwakeword-models/'
echo "Installed. Restart studio-edge on Myra."
