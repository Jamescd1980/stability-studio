#!/usr/bin/env bash
set -eu
echo "=== gpu_backend ==="
~/bin/gpu_backend.sh status 2>/dev/null || echo "no gpu_backend.sh"
echo "=== systemd ==="
systemctl is-active comfyui 2>/dev/null || true
systemctl is-active forge 2>/dev/null || true
systemctl is-active ollama 2>/dev/null || true
systemctl is-active narrate-tts 2>/dev/null || true
echo "=== ports ==="
ss -lntp | grep -E '8188|7860|11434|8090' || true
echo "=== rocm ==="
rocm-smi 2>/dev/null | head -45 || true
echo "=== top mem procs ==="
ps -eo pid,pcpu,pmem,rss,cmd --sort=-rss | head -20
echo "=== python/comfy hints ==="
ps -eo pid,cmd | grep -iE 'comfy|forge|webui|python' | grep -v grep | head -30
