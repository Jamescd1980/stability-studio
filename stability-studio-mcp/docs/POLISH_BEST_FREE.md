# Best free Wan polish (main rig)

**Host:** Ryzen 7900X + RTX 5060 Ti (16 GB)  
**Role:** post only — generate / splice keepers on ComfyBox first  
**Goal:** fix mid-clip quality slips better than ffmpeg `minterpolate` + AnimeSharp alone

## Order of operations

**Clean before you invent frames.** RIFE synthesizes in-betweens from whatever you give it. If mid-clip eyes/faces are mush, RIFE→SeedVR2 spreads and “restores” that mush — Saloon keepers have looked *worse* after polish for this reason.

**2026-08-20 (Saloon SS02):** SeedVR-only @1080 on `SS02_i2v_thrust_33f_v7_KEEP` — owner preferred the **original**. Recycle polish fails; do not treat SeedVR as automatic upgrade on already-sharp keepers. For “clean existing clip,” prefer catalog **`v2v_upscale`** latent denoise (mute RIFE) once ComfyBox packs are up — **not** MCP `mode=v2v` (that only extends).

1. **Lock the cut** — approved keeper / concat only. Do not polish WIP fails.
2. **Identity / quality cleanup at native fps** (optional but preferred when faces matter):
   - Trim melt/blur tails; or
   - **EBSynth** (HQ still → guide frames); or
   - SeedVR2 alone on the 16 fps master (`polish_wan_best(..., skip_interpolate=true)`)
3. **RIFE last** — only after the native frames already look good (16 → 24/32).
4. Optional light SeedVR2 pass after RIFE only if the cleaned cut still needs upscale — never use RIFE→SeedVR2 as a face-repair ladder.
5. **Deliver** — gate again; keep AnimeSharp path for fast drafts only.

Default MCP `polish_wan_best` still runs RIFE→SeedVR2 for convenience. Prefer **SeedVR-first / skip_interpolate** (or EBSynth then RIFE) when identity is fragile.

Do **one GPU job at a time**. Do not run SeedVR2 while ComfyBox is also hammering a shared remote GPU (this stack is local 5060 Ti).

## What is installed (paths)

| Piece | Path |
|---|---|
| RIFE-ncnn-vulkan (TNTwise 20250112) | `D:\studio-agent\stability-studio-mcp\tools\rife\` (junction) |
| RIFE exe | `...\tools\rife\rife-ncnn-vulkan.exe` |
| Default RIFE model | `rife-v4.26` (also `rife-anime`, `rife-v4.25`, …) |
| SeedVR2 CLI repo | `D:\studio-agent\stability-studio-mcp\tools\seedvr2_videoupscaler\` |
| SeedVR2 venv | `...\seedvr2_videoupscaler\.venv\` (Py 3.10 + torch cu128) |
| DiT weight (3B FP8) | `...\models\SEEDVR2\seedvr2_ema_3b_fp8_e4m3fn.safetensors` (~3.4 GB) |
| VAE | `...\models\SEEDVR2\ema_vae_fp16.safetensors` (~501 MB) |
| AnimeSharp fallback | `D:\StabilityMatrix-win-x64\Data\Models\RealESRGAN\2x-AnimeSharpV4_RCAN.safetensors` |
| Legacy polish venv | `D:\studio-agent\stability-studio-mcp\.venv-post\` |

Config keys live under `local_post:` in `config.yaml`.

## VRAM tips (5060 Ti 16 GB)

**Best we can run locally (default):**

- SeedVR2 **3B FP8**
- `blocks_to_swap=16`, `swap_io_components`
- VAE encode/decode **tiled**
- `batch_size=5` (must be `4n+1`)
- short-side `--resolution 1080` (720² Wan → ~1080)

If OOM: raise `blocks_to_swap` to 24–32, drop resolution to 720–900, or use GGUF Q8/Q4 (download into same `models/SEEDVR2`).

**Wishlist if more VRAM (24 GB+):**

- SeedVR2 **7B FP16 / 7B sharp**
- `blocks_to_swap=0`, larger `batch_size` (21–81)
- short-side 1440–2160
- optional Flash Attention / SageAttention / Triton compile

FlashVSR+ was **not** installed — SeedVR2 3B FP8 fits; use FlashVSR+ only if you want a faster diffusion-VSR experiment later.

## How to call (agent / MCP)

```text
check_local_post()
# expect best_path_ok: true, rife.present, seedvr2.present

polish_wan_best(video_path="D:/.../keeper.mp4", target_fps=24,
                seedvr2_resolution=1080, seedvr2_batch_size=5,
                seedvr2_blocks_to_swap=16)
```

Or staged:

```text
interpolate_video(video_path=..., target_fps=24, method="rife")
# then polish_wan_best(..., skip_interpolate=true)  # SeedVR2 only
```

Legacy / fast:

```text
polish_wan_video(video_path=..., interpolate_method="minterpolate",
                 upscale_model="anime_sharp_2x")
```

## How to call (CLI)

```powershell
cd D:\studio-agent\stability-studio-mcp

# Status
.\.venv-post\Scripts\python.exe scripts\general\local_post\polish_wan_best.py --check-only

# Full best path
.\.venv-post\Scripts\python.exe scripts\general\local_post\polish_wan_best.py `
  --input "D:\ComfyBox Images and Videos\Video\Frieren\Saloon\SS03_1_v2_T1.mp4" `
  --target-fps 24 --resolution 1080

# Smoke (limit frames)
.\.venv-post\Scripts\python.exe scripts\general\local_post\polish_wan_best.py `
  --input "...\SS03_1_v2_T1.mp4" --max-frames 32 --resolution 1080
```

Direct SeedVR2 (UTF-8 required on Windows):

```powershell
$env:PYTHONUTF8=1
& tools\seedvr2_videoupscaler\.venv\Scripts\python.exe `
  tools\seedvr2_videoupscaler\inference_cli.py input.mp4 `
  --model_dir tools\seedvr2_videoupscaler\models\SEEDVR2 `
  --dit_model seedvr2_ema_3b_fp8_e4m3fn.safetensors `
  --resolution 1080 --batch_size 5 `
  --dit_offload_device cpu --vae_offload_device cpu `
  --blocks_to_swap 16 --swap_io_components `
  --vae_encode_tiled --vae_decode_tiled `
  --video_backend ffmpeg
```

## Honest quality ladder

| Rank | Stack | When |
|---|---|---|
| 1 | **EBSynth / trim → SeedVR2 @16fps → RIFE** | Identity-critical NSFW (preferred) |
| 2 | **SeedVR2 only** (`skip_interpolate=true`) then RIFE | Mid mush without a still key |
| 3 | RIFE → SeedVR2 3B FP8 | Smooth already-clean keepers only |
| 4 | RIFE → AnimeSharp 2× | Faster draft |
| 3 | minterpolate → AnimeSharp | Legacy / CPU-only interp |
| Paid | Topaz etc. | Not used here |

TensorRT RIFE builds were skipped: Blackwell (50-series) TRT packaging is fragile; **ncnn-vulkan** is the practical Windows quality path on this card.
