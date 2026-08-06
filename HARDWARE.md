# GPU hardware profile

Agents should **always** call `get_generation_context` before `generate_image` or `generate_video`. The response includes:

- **`hardware_profile`** — detected GPU, VRAM, `gpu_only`, `prefer_prompt_quality`
- **`generation_limits`** — safe caps for resolution, steps, frames, and I2V settings

Logic lives in `stability-studio-mcp/studio/hardware_profile.py`.

## Division of labor (book names)

| Name | Where | Role |
|------|-------|------|
| **Myra** | Pi 5 (`myra` / `192.168.50.230`) | Voice + **Gofor** (`myra-gofor` on Pi Ollama) — sort/funnel, room tools |
| **Nari** | LinuxBox/ComfyBox `192.168.50.57` **8600G CPU** Ollama `:11434` | Create / Forge refine / Wan clip language brain |
| **nari-prompt** | Same LinuxBox Ollama | Eric's Prompt Enhancers only |
| **Orla** | Windows main rig `192.168.50.42` **7900X CPU** Ollama `:11434` + tools `:11436` | Open/display, upscale, RIFE/interp, **Kokoro / phonetic chapter prep** |
| **RTX 5090** | LinuxBox dGPU (CUDA) | ComfyUI `:8188` diffusion / Wan (32GB); **Blender MCP** `:9876` (exclusive vs Comfy) |
| **5060 Ti** | Windows dGPU | Polish GPU jobs (not chat) |

Voice path: **You → Myra (gofor) → ask_nari / ask_orla / local tools**.  
Hey Jan wake still greets Nari (direct studio). Follow-up listen window skips re-wake.

LinuxBox Ollama: `OLLAMA_NUM_GPU=0` so Nari does not steal 5090 VRAM.  
SSH: `ssh Linuxbox` (alias `comfybox`) → `192.168.50.57`.  
Blender MCP: [BLENDER-MCP.md](BLENDER-MCP.md) — Blender on LinuxBox 5090, Cursor `BLENDER_HOST=192.168.50.57:9876`; `~/bin/gpu_backend.sh blender|comfy` for exclusivity.  
CUDA migration lessons: [LESSONS-COMFYBOX-CUDA.md](LESSONS-COMFYBOX-CUDA.md). Blender lessons: [LESSONS-BLENDER-MCP.md](LESSONS-BLENDER-MCP.md).  
Modelfiles: `ollama/nari/`, `ollama/myra-gofor/`, `ollama/orla/`.

### MCP source of truth

- **Windows** `D:\studio-agent\stability-studio-mcp` is the main MCP repo (Cursor/Jan).
- **LinuxBox** `/mnt/game/studio-agent/stability-studio-mcp` is a **one-way mirror** for backup.
- Sync after catalog/code changes: `py -3 scripts/sync_mcp_to_comfybox.py` (writes `SYNCED_FROM_WINDOWS.txt`).
- Do **not** edit catalog only on LinuxBox.
- Voice cast: Myra uses local `handoff/myra-patches/cast/` lists (export via `scripts/general/export_cast_lists.py`); Nari expands scene after IDs are locked.

| Brain | LAN |
|-------|-----|
| Myra gofor | `http://127.0.0.1:11434` on Pi (`myra-gofor`) |
| Nari | `http://192.168.50.57:11434` |
| Orla | `http://192.168.50.42:11434` + tools `:11436` |

Eric node: `ollama` → `http://127.0.0.1:11434` → `model_name=nari-prompt`

Rule of thumb: **gofor on Pi, generate on the RTX 5090 (Nari/LinuxBox), polish/display on Windows (Orla).**  
`get_generation_context` returns `labor_split` with the generation/polish policy.

## Config overrides (`config.yaml`)

```yaml
hardware:
  vram_gb: 0                 # 0 = auto-detect from ComfyUI /system_stats
  gpu_only: true             # lower res/frames instead of CPU offload
  prefer_prompt_quality: true  # anatomy/face in prompt, not max pixels
```

Set `vram_gb` manually if ComfyUI is offline but you know your card (e.g. `16` for RTX 5060 Ti 16GB).

## What “high quality” means here

When `prefer_prompt_quality` is true:

- **Do** use strong prompts/negatives for face, hands, and anatomy.
- **Do not** max out resolution or frame count unless the user explicitly asks.
- **Do** stay within `generation_limits` for the detected VRAM tier.

## VRAM tiers (auto)

| VRAM | Image max | I2V default |
|------|-----------|-------------|
| ≤8 GB | 768×1024 | **`i2v_5b`**, 416×576, 49 frames @ 16fps |
| ≤12 GB | 896×1152 | **`i2v_5b`**, 480×640, 49 frames @ 16fps |
| ≤16 GB | 1024×1216 | **`i2v_5b`**, 704×1056, 65 frames @ 16fps; **`t2v`**, 81 frames @ 16fps |
| ≤24 GB | 1024×1536 | **`i2v_5b`**, 832×480, 81 frames @ 16fps |
| 32 GB+ | 1216×1664 | **`i2v_5b`** or explicit **`i2v_gpu`** |

## I2V paths

| `workflow_id` | Model | When |
|---------------|-------|------|
| **`i2v_5b`** (default) | Wan 2.2 TI2V-5B native ComfyUI | Drafts / SFW; often weak/censored for NSFW |
| **`i2v`** | **Wan 2.2 I2V-A14B MoE HIGH+LOW** | Explicit 14B / identity / NSFW motion |
| **`i2v_wan21_native`** | Legacy Wan 2.1 single-UNET | Fallback / A/B only — prefer `i2v` |
| **`i2v_gpu`** | Wan 2.1 14B builder | 24 GB+ or forced; can hang on 16 GB |

**`i2v` MoE wiring (MCP `studio.wan22_i2v_moe`):** HIGH UNET (+ HIGH LoRAs) → KSamplerAdv → LOW UNET (+ LOW LoRAs) → KSamplerAdv → decode. Default stacks LightX2V distill when installed; action LoRAs must be HIGH+LOW pairs (`female_orgasm`).

Assets: `check_wan_assets(workflow_id="i2v")` / `download_wan_assets` + `scripts/general/download_wan22_lightning_loras.py`. Orgasm NSFW LoRAs already on ComfyBox. See `stability-studio-mcp/LESSONS-WAN-I2V.md`. NSFW kits live under `scripts/nsfw/`.

## For agents

1. `get_generation_context`
2. Read `generation_limits.video_i2v` or `generation_limits.image`
3. Generate within caps
4. Only one ComfyUI instance — never launch twice (port 8188 / DB lock)
5. Avoid **parallel video jobs** on ≤16 GB — can OOM or drop ComfyUI (validated 2026-06-11)
