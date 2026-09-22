# GPU hardware profile

Agents should **always** call `get_generation_context` before `generate_image` or `generate_video`. The response includes:

- **`hardware_profile`** — detected GPU, VRAM, `gpu_only`, `prefer_prompt_quality`
- **`generation_limits`** — safe caps for resolution, steps, frames, and I2V settings

Logic lives in `stability-studio-mcp/studio/hardware_profile.py`.

## Division of labor (book names)

| Name | Where | Role |
|------|-------|------|
| **EdgeVoice** | Pi 5 (`myra` / `EDGE_HOST`) | Voice + **Gofor** (`myra-gofor` on Pi Ollama) — sort/funnel, room tools |
| **CreateBrain** | GENERATION_HOST/GenerationHost `GENERATION_HOST` Ollama `:11434` | Create brain — **5090 CUDA when free**; MCP unloads before Wan/audio |
| **nari-prompt** | Same Ollama | Eric Prompt Enhancers only (also unloaded before Wan) |
| **DeskHost** | Windows main rig `DESK_HOST` (**PC name**) | Desk host — **Coder** on the 5060 Ti (game code/install). Not a create chat persona |
| **RTX 5090** | GENERATION_HOST dGPU | ComfyUI / Forge / Wan **and** CreateBrain chat when diffusion is light |
| **5060 Ti** | Windows dGPU | **Coder only** (Ollama `num_gpu` full). Create/diffusion stays on GenerationHost — no Invoke↔coder GPU split here |

Voice path: **You → EdgeVoice (gofor) → ask_nari / ask_orla / local tools**.  
Hey Jan wake still greets CreateBrain (direct studio). Follow-up listen window skips re-wake.

GENERATION_HOST Ollama: CreateBrain may use the **5090** for chat. MCP `generate_video` / `generate_audio` / `generate_video_hero` **unload** `nari` + `nari-prompt` first. Do not leave a 128K context pinned.  
SSH: `ssh GENERATION_HOST` (alias `generation-host`) → `GENERATION_HOST`.  
Manual: `ssh GENERATION_HOST '~/bin/nari_gpu.sh unload|status'` or MCP `unload_nari_for_gpu`.  
Blender MCP: [BLENDER-MCP.md](BLENDER-MCP.md) — Blender on GENERATION_HOST 5090, Cursor `BLENDER_HOST=GENERATION_HOST:9876`; `~/bin/gpu_backend.sh blender|comfy` for exclusivity.  
CUDA migration lessons: [LESSONS-COMFYBOX-CUDA.md](LESSONS-COMFYBOX-CUDA.md). Blender lessons: [LESSONS-BLENDER-MCP.md](LESSONS-BLENDER-MCP.md).  
Modelfiles: `ollama/nari/`, `ollama/myra-gofor/`, `ollama/orla/`.

### MCP source of truth

- **Windows** `D:\studio-agent\stability-studio-mcp` is the main MCP repo (Cursor/Jan).
- **GENERATION_HOST** `<MODELS_MOUNT>/studio-agent/stability-studio-mcp` is a **one-way mirror** for backup.
- Sync after catalog/code changes: `py -3 scripts/sync_mcp_to_generation-host.py` (writes `SYNCED_FROM_WINDOWS.txt`).
- Do **not** edit catalog only on GENERATION_HOST.
- Voice cast: EdgeVoice uses local `handoff/myra-patches/cast/` lists (export via `scripts/general/export_cast_lists.py`); CreateBrain expands scene after IDs are locked.

| Brain | LAN |
|-------|-----|
| EdgeVoice gofor | `http://127.0.0.1:11434` on Pi (`myra-gofor`) |
| CreateBrain | `http://GENERATION_HOST:11434` |
| DeskHost | `http://DESK_HOST:11434` + **Coder toolcall proxy** `:11436` (OI must use `:11436`) |

Eric node: `ollama` → `http://127.0.0.1:11434` → `model_name=nari-prompt`

Rule of thumb: **gofor on Pi, generate on the RTX 5090 (CreateBrain/GENERATION_HOST), polish/display on Windows (DeskHost).**  
`get_generation_context` returns `labor_split` with the generation/polish policy.

**Touch-ups (2026-09-22):** Hand cleanup / custom paint AI struggles with → **Krita on DeskHost**. Diffusion inpaint/refine → **GenerationHost** (Forge/Comfy) when the 5090 is free — not local **Invoke** on the 5060 while GenerationHost sits idle. Invoke folders may remain archival masters only.

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

Assets: `check_wan_assets(workflow_id="i2v")` / `download_wan_assets` + `scripts/general/download_wan22_lightning_loras.py`. Orgasm NSFW LoRAs already on GenerationHost. See `stability-studio-mcp/LESSONS-WAN-I2V.md`. NSFW kits live under `scripts/nsfw/`.

## For agents

1. `get_generation_context`
2. Read `generation_limits.video_i2v` or `generation_limits.image`
3. Generate within caps
4. Only one ComfyUI instance — never launch twice (port 8188 / DB lock)
5. Avoid **parallel video jobs** on ≤16 GB — can OOM or drop ComfyUI (validated 2026-06-11)
