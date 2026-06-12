# MOSS audio generation (ComfyUI)

Agents: call **`get_generation_context`** — includes `moss_audio`, `media_paths`, and `wan2gp_assets`.

## Known issues (June 2026)

| Mode | Status |
|------|--------|
| **voice_design** | ✅ Working via MCP (`generate_audio(mode=voice_design, ...)`) |
| **speech** (Local 1.7B) | ❌ `MossTTSDelayConfig` / `num_hidden_layers` — update `comfyui-moss-tts` + `transformers` in ComfyUI venv, restart ComfyUI |
| **sound_effect** | Heavy (~18 GB); avoid parallel GPU jobs on 16 GB |

Log: `outputs/priority_implementation_log.json`

## One-time setup

1. Custom node: `ComfyUI/custom_nodes/comfyui-moss-tts` (cloned from [richservo/comfyui-moss-tts](https://github.com/richservo/comfyui-moss-tts))
2. `pip install -r requirements.txt` in ComfyUI venv
3. Restart ComfyUI
4. `check_moss_assets` → `download_moss_assets` (or `python scripts/download_moss_assets.py`)

Models cache to `ComfyUI/models/moss-tts/`.

## MCP tools

| Tool | Use |
|------|-----|
| `check_moss_assets` | Node + model readiness |
| `download_moss_assets` | Hugging Face download |
| `generate_audio` | Run MOSS in ComfyUI |
| `list_media_paths` | Output folders for images/audio/video |

## Timing (important)

MOSS uses **12.5 audio tokens per second** ([OpenMOSS docs](https://github.com/OpenMOSS/MOSS-TTS/blob/main/docs/moss_voice_generator_model_card.md)).

| Mode | How to control length |
|------|------------------------|
| **voice_design** | Pass `duration_seconds` to MCP (sets internal `tokens` field). **Do not** put “3 seconds” in `instruction` — the model acts that out as filler before speech. |
| **speech** (Local 1.7B) | `enable_duration_control` + `duration_tokens` in ComfyUI Generate node |
| **sound_effect** | `duration_seconds` on the SFX node |

**instruction** = voice character only: timbre, pitch, age, emotion, accent. Examples from OpenMOSS:

- EN: `Warm, gentle female voice with calm delivery`
- Prosody OK: `even tempo`, `slow complaint` (quality, not wall-clock seconds)

**max_new_tokens** = hard ceiling; **tokens** (voice design) / **duration_tokens** (speech) = target length hint (approximate).

After ComfyUI restart, Voice Design node exposes `enable_duration_control` + `duration_seconds` (patched locally).

## Modes

```text
generate_audio(mode="speech", text="Hello world", language="en")
generate_audio(mode="sound_effect", prompt="footsteps on gravel", duration_seconds=5)
generate_audio(mode="voice_design", text="Welcome back.", instruction="warm female narrator, calm")
```

Outputs: `ComfyUI/output/audio/*.mp3` (also copied to MCP `outputs/` when saved via ComfyUI history).

## Workflows (manual ComfyUI)

Bundled API templates in `stability-studio-mcp/workflows/` and `bundled-workflows/`:

- `workflow-moss-tts-speech-api.json`
- `workflow-moss-sfx-api.json`
- `workflow-moss-voice-design-api.json`

Load the inner `"workflow"` object as an API prompt, or build graphs with nodes under **audio/MOSS-TTS**.

## VRAM (16 GB)

| Model | VRAM | Speed |
|-------|------|-------|
| Local 1.7B TTS | ~5 GB | Fast — default |
| SoundEffect 8B | ~18 GB | Slow; unload other models first |
| VoiceGenerator 8B | ~18 GB | Slow |

Do not run MOSS 8B while a Wan video job is queued on the same GPU.

## Wan2GP (hero video via MCP)

MCP **`generate_video_hero`** runs Wan2GP Enhanced Lightning v2 headless (MCP on `:7867`). ComfyUI **`generate_video`** remains the draft 5B path.

- Check assets: `check_wan2gp_assets` → `download_wan2gp_assets`
- Runtime: `check_wan2gp_runtime` · `check_gpu_backend` (stop ComfyUI + Wan2GP Gradio first)
- Validated bow: `outputs/wan2gp_bow_hero_result.json` (2026-06-12)
- Launch fixes: `outputs/wan2gp_mcp_launch_fix.json`
- Next test (audio overlay): `outputs/kitsune_bow_audio_overlay_plan.json`
- Delivery: `media_paths.delivery` (e.g. Desktop/New Images)

See **`config-examples/jan-assistant-media-paths.md`** for Jan/Myra assistant instructions.
