# Lessons learned — GenerationHost CUDA 5090 migration

Updated **2026-08-20**. Host: GENERATION_HOST / GenerationHost (ex-7900 XT ROCm → RTX 5090 CUDA).

## Verdict

ROCm was a dead end for this box once the 5090 landed. Fresh **CUDA 12.8 PyTorch** in a new ComfyUI `.venv`, **nvidia-driver-595-open**, models on the **Game** drive (`/mnt/game`), and MCP `vram_gb: 32` is the working path. Do not keep a ROCm fallback “just in case.”

## What worked

| Step | Lesson |
|------|--------|
| Purge ROCm before CUDA | Mixed stacks fight for `/dev/kfd` and confuse agents. One stack only. |
| Fresh `.venv`, not in-place upgrade | Old ROCm torch wheels poison `pip install torch`. Use `scripts/generation-host_cuda_venv.sh`. |
| Driver: `nvidia-driver-595-open` | Matched Blackwell / 5090 on Ubuntu; verify with `nvidia-smi` before blaming Comfy. |
| Models on Game (4TB NTFS) | OS disk (~256GB) is too small for Wan MoE + Hunyuan. Keep DiffusionModels / outputs under `<MODELS_MOUNT>/...`. |
| MCP mirror is one-way | Edit catalog/code on Windows `D:\studio-agent`; sync to GENERATION_HOST. Never invent catalog only on the box. |
| MoE I2V smoke | Draft then quality **65f ~736×1088** validated post-migration. Caps in `hardware_profile` must match 32 GB. |
| Kohya CUDA `.venv` on Game | Same rule as Comfy: CUDA torch on 5090; ignore noisy tensorflow pin warnings if training starts. |
| Hunyuan 1.5 assets | `check_hunyuan_assets` / `download_hunyuan_assets` are enough for now; **`generate_video` Hunyuan routing still TBD**. |
| **V2V clean packs (2026-08-20)** | Live ComfyUI is `~/ComfyUI` — **not** the full Game SM `custom_nodes` tree. Symlink Game packs (`comfyui-kjnodes`, `ComfyUI-Frame-Interpolation`) + clone `rgthree-comfy`, `ComfyUI-wanBlockswap`. Then `gpu_backend.sh stop-comfy` → `comfy`. Fast Muter = UI-only. |

## Pitfalls

1. **Network before GPU work** — WiFi/static IP/SSH must be solid (`GENERATION_HOST` / `generation-host` → `.57`). Agent “hangs” were often LAN, not CUDA.
2. **ComfyUI + Blender + Forge on one 5090** — exclusive backends. Use `~/bin/gpu_backend.sh` (`comfy` \| `blender` \| `forge` \| `stop-all`).
3. **Missing `clear_installed_node_types_cache`** — broke MCP dep checks after node installs; fixed in `studio/comfy_deps.py`. Restart MCP after pulling that fix.
4. **Public vs private git** — LAN IPs, cast lists, NSFW one-off runners belong on **Private-Studio** or stay local. Public hub: scrubbed examples + generic scripts.
5. **`install_comfyui_dependencies` on Windows SM path** does not populate GENERATION_HOST `~/ComfyUI/custom_nodes` — SSH install/symlink there for GenerationHost.
6. **MCP `mode=v2v` ≠ clean** — extend only. Latent clean = catalog `v2v_upscale` (mute RIFE). SeedVR polish can lose to the original (Saloon SS02).

## Scripts (repo)

| Script | Role |
|--------|------|
| `scripts/generation-host_cuda_bootstrap.sh` | Host prep / driver notes |
| `scripts/generation-host_cuda_venv.sh` | ComfyUI CUDA venv |
| `scripts/generation-host_kohya_cuda_venv.sh` | Kohya CUDA venv |
| `scripts/generation-host_download_hunyuan15.sh` | Hunyuan weight fetch |
| `scripts/generation-host_gpu_backend.sh` | Source for `~/bin/gpu_backend.sh` |

Backups from migration: `<MODELS_MOUNT>/backups/cuda-migration-*` (on box only — do not commit).

## Related

- [HARDWARE.md](HARDWARE.md) — labor split, 32 GB tiers
- [MODEL-FAMILIES.md](MODEL-FAMILIES.md) — Hunyuan 1.5 rows
- [LESSONS-BLENDER-MCP.md](LESSONS-BLENDER-MCP.md) — Blender on same GPU
- [stability-studio-mcp/LESSONS-WAN-I2V.md](stability-studio-mcp/LESSONS-WAN-I2V.md) — MoE keeper rules

### Idle GPU vs local Invoke (2026-09-22)

- If GenerationHost is idle, send AI touch-ups/custom renders there (Forge/Comfy). Use DeskHost Krita for manual cleanup. Avoid local Invoke competing with Coder on the 5060 Ti for work the 5090 should own.  
<!-- appended 2026-09-22 via append_lesson -->

### Coder OI tool calls (2026-09-22)

- qwen2.5-coder via Ollama returns tool JSON in message.content, not tool_calls — OI/Codex will not execute. Fix: DeskHost proxy D:\studio-agent\ollama\coder\ollama_toolcall_proxy.py on 127.0.0.1:11436 rewriting content→tool_calls; point Coder OI profile at :11436/v1 (start_toolcall_proxy.ps1). Raw :11434 will keep dumping JSON.  
<!-- appended 2026-09-22 via append_lesson -->

### Coder model (2026-09-22)

- Coder upgraded 2026-09-22: coder:latest FROM qwen3-coder:30b (Qwen3 MoE) on DeskHost 5060 Ti; keep :11436 toolcall proxy for OI. qwen2.5-coder:14b is legacy fallback only.  
<!-- appended 2026-09-22 via append_lesson -->
