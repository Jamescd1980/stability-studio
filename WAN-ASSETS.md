# Wan video assets (I2V / T2V)

Agents: call **`get_generation_context`** before video generation — includes **`wan_video_assets`** (base models) and **`wan_video_loras`** (optional LoRAs).

## Modes in this repo

| Path | What it needs | Default? |
|------|----------------|----------|
| **`i2v_5b`** | `wan2.2_ti2v_5B_fp16`, `wan2.2_vae`, `umt5_xxl_fp8_e4m3fn_scaled` | ✅ **Default I2V** on all tiers |
| **`i2v_5b_painter`** | Same as `i2v_5b` + **ComfyUI-PainterI2V** custom node | Motion `motion_amplitude` (1.0–1.5) |
| **`v2v_5b`** | Same assets as `i2v_5b` — extend a clip from its last frame | `mode=v2v` + `video_path` |
| **`v2v_5b_painter`** | V2V extend + PainterI2V motion | ✅ **Default V2V** |
| **`t2v`** | `wan2.1_t2v_1.3B`, umt5, `wan_2.1_vae` | ✅ Default T2V |
| **`i2v`** | 2× Wan 2.2 14B I2V + distill LoRA | Legacy; explicit `workflow_id=i2v` only |
| **`i2v_gpu`** | `wan2.1_i2v_480p_14B` | Optional; VRAM-heavy on 16 GB |
| **`i2v_wan21`** | Self-Forcing VACE + rank32 LoRA | Extra models |

## Base model download

```powershell
cd stability-studio-mcp
python scripts/download_wan_assets.py --workflow i2v_5b --include-large
```

Or in chat: `download_wan_assets(workflow_id="i2v_5b", include_large=true)`

Restart **ComfyUI** from Stability Matrix after large downloads complete.

## Optional video LoRAs (motion / face / lighting)

Manifest: `studio/wan_video_loras.py` (Hugging Face: [wangkanai/wan22-fp16-i2v-loras](https://huggingface.co/wangkanai/wan22-fp16-i2v-loras)).

| Id | Purpose |
|----|---------|
| `face_naturalizer` | More natural face / head motion |
| `light_volumetric` | God-rays / volumetric church light |
| `camera_steady` | Low-weight orbit (steady aisle dolly) |
| `camera_arc` | Cinematic arc shot |
| `action_wink` | Small gesture reference only |

**Bundles:** `walk_cycle` · `smooth_character` · `cinematic_church` · `motion_boost`

**Machine-local LoRAs:** copy `studio/wan_video_loras_local.example.py` → `studio/wan_video_loras_local.py` (gitignored) to register extra community LoRAs without editing shipped manifests.

There is **no dedicated anti-clipping LoRA** — fix source stills (hands in front of cloak) and use PainterI2V `motion_amplitude` + prompt constraints.

```powershell
python scripts/download_wan_video_loras.py --bundle smooth_character
python scripts/download_wan_video_loras.py --bundle cinematic_church
python scripts/download_wan_video_loras.py --check
```

## Wan2GP hero (storyboard production clips)

Not a ComfyUI workflow — separate Stability Matrix package + MCP on `:7867`.

| Step | Tool |
|------|------|
| Assets | `check_wan2gp_assets` / `download_wan2gp_assets` |
| Runtime | `check_wan2gp_runtime` |
| GPU | `check_gpu_backend` (stop ComfyUI) |
| Generate | `generate_video_hero` — preset `i2v_2_2_Enhanced_Lightning_v2` |
| Storyboard | [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) — Rin walk/bow/stab |

Validated on 16 GB: 49 frames @ 832×480, `motion_amplitude` 1.05–1.12.

Install log (local): `stability-studio-mcp/outputs/local/` (gitignored)

MCP: `check_wan_video_loras` · `download_wan_video_loras(bundle="walk_cycle")`

Pass to generation:

```text
generate_video(
  mode="i2v",
  image_path="...",
  lora_bundle="walk_cycle",
  use_painter_i2v=true,
  motion_amplitude=1.1,
)
```

## PainterI2V (motion node)

1. `check_painter_i2v_dependencies`
2. `install_painter_i2v_dependencies` → **restart ComfyUI**
3. `generate_video(..., workflow_id="i2v_5b_painter")` or `use_painter_i2v=true`

Lower `motion_amplitude` (e.g. 1.05–1.1) for subtler leg gait; raise toward 1.25 for stronger walk.

## V2V (video → video extend)

Extend an existing clip by continuing from its **last frame** (Wan 2.2 TI2V-5B). By default the MCP **concatenates** source + continuation.

```text
generate_video(
  mode="v2v",
  video_path="<path/to/your_clip.mp4>",
  prompt="anime kitsune girl twirls and winks at camera, cherry blossom park, close-up",
  workflow_id="v2v_5b_painter",
  num_frames=65,
  frame_rate=16,
)
```

| Param | Notes |
|-------|--------|
| `video_path` | Required for `mode=v2v` |
| `concat_source` | Default `true` — output includes `{stem}_v2v_extended.mp4` |
| `workflow_id` | `v2v_5b` or `v2v_5b_painter` (default when empty) |

Workflow JSON: `workflow-wan22-ti2v-5b-v2v-comfyui-native.json` (repo: `stability-studio-mcp/workflows/`).

For multi-segment 16s clips, chain several `v2v` calls or see `scripts/experiments/kitsune_park_extend.py` as a reference.

## Improving video quality (smoother motion + prompt accuracy)

Community tips mapped to **this repo** on a 16 GB GPU:

| Advice | In this stack |
|--------|----------------|
| **Wan 2.2** for prompt adherence | ✅ Default: `i2v_5b` / `v2v_5b` (TI2V-5B). Avoid `i2v` (14B) on 16 GB — OOM / very slow. |
| **Hunyuan / LTX / Mochi** | Not installed. Would need new workflows + models in Stability Matrix. |
| **ControlNet (pose / depth)** | Not wired into Wan I2V graphs yet. Use **still** ControlNet + IP-Adapter for hero frames; keep motion subtle in video prompts. |
| **Lower I2V denoise** | Wan TI2V is latent-conditioned, not img2img denoise — use **`motion_amplitude` 1.15–1.2** with PainterI2V; avoid over-damping on 16 GB. |
| **Lower FPS + interpolate** | `smooth_motion` defaults **12 fps**. Post-process with ffmpeg `minterpolate` or ComfyUI FILM nodes (not in MCP yet). |
| **Keyframe / prompt travel** | Single prompt per clip today. For long shots: chain **`v2v`** with a new prompt per segment. |
| **First + last frame** | Approximated by **`v2v`**: last frame of clip N seeds clip N+1. For explicit end-frame control, add a custom ComfyUI graph. |

### Validated T2V (16 GB, 2026-06-11)

| Cap | Value | Validated |
|-----|-------|-----------|
| `workflow_id` | `t2v` | Wan 2.1 1.3B |
| Max frames | 81 @ 16 fps | ✅ |
| Parallel jobs | — | ❌ avoid on 16 GB |

```text
generate_video(
  mode="t2v",
  prompt="anime kitsune fox girl, cherry blossom park, cinematic motion",
  workflow_id="t2v",
  num_frames=81,
  frame_rate=16,
  style="anime",
)
```

T2V is **text-only** — use **I2V** when you need to match a reference still.

Log: `outputs/kitsune_bow_video_test.json`

### Validated preset (kitsune park walk, 16 GB)

```text
generate_video(
  mode="i2v",
  image_path="<path/to/hero_still.png>",
  prompt="kitsune girl skipping along cherry blossom park path, fluid leg motion",
  workflow_id="i2v_5b_painter",
  use_painter_i2v=true,
  motion_amplitude=1.2,
  smooth_motion=false,
  num_frames=49,
  frame_rate=16,
)
```

### Validated preset (Japanese bow / curtsy from still, 16 GB)

```text
generate_video(
  mode="i2v",
  image_path="<path/to/hero_still.png>",
  prompt="same anime kitsune fox girl, performing polite Japanese ojigi bow, bending forward at waist then returning upright, same character same outfit, smooth natural motion",
  workflow_id="i2v_5b_painter",
  motion_amplitude=1.1,
  smooth_motion=false,
  num_frames=49,
  frame_rate=16,
  style="anime",
)
```

| Quality | Frames | Workflow | Notes |
|---------|--------|----------|-------|
| Quick smoke | 17 | `i2v_5b` | ~1 s |
| Recommended | 49 | `i2v_5b_painter` | Best bow motion; `motion_amplitude` 1.08–1.15 |
| Max clip | 65 | `i2v_5b` | ~4 s; 16 GB catalog cap |

Log: `outputs/video_quality_setup.json` · `outputs/kitsune_bow_video_test.json`

### Hero bow (Wan2GP — recommended for final quality)

Stop ComfyUI and Wan2GP Gradio. Call `check_gpu_backend` → `generate_video_hero`:

```text
generate_video_hero(
  prompt="(at 0 seconds: ...) (at 1 second: polite Japanese ojigi bow ...) (at 2 seconds: returns upright ...)",
  image_path="<path/to/still.png>",
  video_length=49,
  resolution="832x480",
  seed=424242,
  motion_amplitude=1.05,
)
```

| Quality | Backend | Frames | Runtime (16 GB) | Log |
|---------|---------|--------|-----------------|-----|
| **Hero (final)** | Wan2GP Lightning v2 | 49 | ~2 min | `outputs/wan2gp_bow_hero_result.json` |
| Draft (storyboard) | ComfyUI `i2v_5b_painter` | 49 | ~14 min | `outputs/kitsune_bow_video_test.json` |

Launch fix log: `outputs/wan2gp_mcp_launch_fix.json`


`smooth_motion=true` lowers fps (~12), dampens `motion_amplitude` (~1.08), and may load **`smooth_character`** LoRAs on **>16 GB** VRAM. On **16 GB** it produced nearly static clips in testing — prefer **`smooth_motion=false`** + **`motion_amplitude` 1.15–1.2** + PainterI2V only.
- Extra negatives: jitter, morphing, flicker

Manual equivalent:

```text
generate_video(
  mode="i2v",
  image_path="...",
  use_painter_i2v=true,
  motion_amplitude=1.08,
  frame_rate=12,
  lora_bundle="smooth_character",
  num_frames=49,
)
```

**Prompt accuracy:** keep one clear action verb, subject first, environment second; avoid stacking contradictory motion (“runs” + “stands still”). Match food group on the source still (`ilustmix` for anime).

## Config

See [HARDWARE.md](HARDWARE.md) for GPU caps. Base manifest: `studio/wan_assets.py`. LoRA catalog: `studio/wan_video_loras.py`.
