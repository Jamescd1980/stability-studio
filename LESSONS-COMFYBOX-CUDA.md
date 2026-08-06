# Lessons learned — ComfyBox CUDA 5090 migration

Updated **2026-08-05**. Host: LinuxBox / ComfyBox (ex-7900 XT ROCm → RTX 5090 CUDA).

## Verdict

ROCm was a dead end for this box once the 5090 landed. Fresh **CUDA 12.8 PyTorch** in a new ComfyUI `.venv`, **nvidia-driver-595-open**, models on the **Game** drive (`/mnt/game`), and MCP `vram_gb: 32` is the working path. Do not keep a ROCm fallback “just in case.”

## What worked

| Step | Lesson |
|------|--------|
| Purge ROCm before CUDA | Mixed stacks fight for `/dev/kfd` and confuse agents. One stack only. |
| Fresh `.venv`, not in-place upgrade | Old ROCm torch wheels poison `pip install torch`. Use `scripts/comfybox_cuda_venv.sh`. |
| Driver: `nvidia-driver-595-open` | Matched Blackwell / 5090 on Ubuntu; verify with `nvidia-smi` before blaming Comfy. |
| Models on Game (4TB NTFS) | OS disk (~256GB) is too small for Wan MoE + Hunyuan. Keep DiffusionModels / outputs under `/mnt/game/...`. |
| MCP mirror is one-way | Edit catalog/code on Windows `D:\studio-agent`; sync to LinuxBox. Never invent catalog only on the box. |
| MoE I2V smoke | Draft then quality **65f ~736×1088** validated post-migration. Caps in `hardware_profile` must match 32 GB. |
| Kohya CUDA `.venv` on Game | Same rule as Comfy: CUDA torch on 5090; ignore noisy tensorflow pin warnings if training starts. |
| Hunyuan 1.5 assets | `check_hunyuan_assets` / `download_hunyuan_assets` are enough for now; **`generate_video` Hunyuan routing still TBD**. |

## Pitfalls

1. **Network before GPU work** — WiFi/static IP/SSH must be solid (`Linuxbox` / `comfybox` → `.57`). Agent “hangs” were often LAN, not CUDA.
2. **ComfyUI + Blender + Forge on one 5090** — exclusive backends. Use `~/bin/gpu_backend.sh` (`comfy` \| `blender` \| `forge` \| `stop-all`).
3. **Missing `clear_installed_node_types_cache`** — broke MCP dep checks after node installs; fixed in `studio/comfy_deps.py`. Restart MCP after pulling that fix.
4. **Public vs private git** — LAN IPs, cast lists, NSFW one-off runners belong on **Private-Studio** or stay local. Public hub: scrubbed examples + generic scripts.

## Scripts (repo)

| Script | Role |
|--------|------|
| `scripts/comfybox_cuda_bootstrap.sh` | Host prep / driver notes |
| `scripts/comfybox_cuda_venv.sh` | ComfyUI CUDA venv |
| `scripts/comfybox_kohya_cuda_venv.sh` | Kohya CUDA venv |
| `scripts/comfybox_download_hunyuan15.sh` | Hunyuan weight fetch |
| `scripts/comfybox_gpu_backend.sh` | Source for `~/bin/gpu_backend.sh` |

Backups from migration: `/mnt/game/backups/cuda-migration-*` (on box only — do not commit).

## Related

- [HARDWARE.md](HARDWARE.md) — labor split, 32 GB tiers
- [MODEL-FAMILIES.md](MODEL-FAMILIES.md) — Hunyuan 1.5 rows
- [LESSONS-BLENDER-MCP.md](LESSONS-BLENDER-MCP.md) — Blender on same GPU
- [stability-studio-mcp/LESSONS-WAN-I2V.md](stability-studio-mcp/LESSONS-WAN-I2V.md) — MoE keeper rules
