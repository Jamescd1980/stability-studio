# Storyboard quickstart

Build a **linked character sequence** (visual novel / book trailer beat) with hero motion, optional MOSS dialogue, and frame-accurate splice. Validated on the **Rin** kitsune scene (walk → bow → lunge).

## What you get

| Layer | Tool | Rin example |
|-------|------|-------------|
| Hero still | `generate_image` / i2i | `images/Rin_kitsune_approved.png` |
| Hero clips | `generate_video_hero` (Wan2GP Lightning v2) | `clips/Rin_clip1_walk.mp4` … |
| Dialogue | `generate_audio` (MOSS `voice_design`) | `audio/Rin_dialogue_01_greetings.mp3` … |
| Lip sync (optional) | Wan2GP Infinitetalk | VRAM-heavy; skip on 16 GB if needed |
| Final | ffmpeg splice (no duplicate chain frames) | `final/Rin_storyboard_spliced.mp4` |

## Project folder layout

Set `outputs.delivery` in `config.yaml` to your project root:

```
MyProject/
  source/           # original reference upload
  images/           # hero stills
  images/chain/     # *_last_frame.png for I2V handoff
  assets/           # canny, lineart, openpose — not character stills
  clips/            # approved hero MP4s (one canonical name per beat)
  audio/            # approved MP3
  temp/             # raw Wan2GP/MOSS until you approve
  logs/             # JSON run logs only
  final/            # spliced or muxed deliverable
  rejected/         # superseded attempts (optional)
```

See `scripts/storyboard/examples/recommended_project_layout.json` and [PATHS.md](PATHS.md).

**Avoid triple files:** Wan2GP writes timestamp MP4s to `temp/` → promote **one** file to `clips/` with a fixed name. Do not leave timestamp + `_2` + canonical copies in the same folder.

## Wan2GP hero path (production motion)

Wan2GP runs **headless** on MCP port **7867** — never alongside ComfyUI on 16 GB.

| Step | Tool | Notes |
|------|------|-------|
| Preflight | `check_wan2gp_runtime` | Assets + MCP reachable |
| GPU lock | `check_gpu_backend` | Stop ComfyUI first |
| Generate | `generate_video_hero` | Lightning v2, 49 frames, 832×480 |
| Promote | manual or script | `temp/` → `clips/Rin_clipN_*.mp4` |

**Rin validated preset:** `motion_amplitude=1.05`, `seed=424242`, ~125 s/clip on 16 GB.

Draft ComfyUI (`i2v_5b_painter`) remains useful for iteration; hero Wan2GP for final storyboard clips.

## MCP workflow (16 GB GPU)

```
get_generation_context
check_storyboard_readiness
check_gpu_backend
```

### 1. Plan (no GPU)

```
plan_storyboard_scene(
  script=\"\"\"
walk toward camera | Greetings.
polite Japanese bow | My name is Rin, you killed my father.
lunge toward camera | Now prepare to die.
\"\"\",
  hero_image="C:/.../images/Rin_kitsune_approved.png",
  food_group="anime",
  voice_instruction="young woman, soft Japanese accent, polite, close-mic",
  include_lipsync=false,
  splice_clips=true,
  fade_last_beat=true,
)
```

### 2. Hero clips (Wan2GP only)

Stop ComfyUI. For each beat:

```
check_gpu_backend
generate_video_hero(
  image_path="<chain frame or hero still>",
  prompt="...",
  video_length=49,
  resolution="832x480",
  motion_amplitude=1.05,
)
```

Extract last frame → `images/chain/` → next beat's `image_path`.

### 3. Audio (ComfyUI only)

Stop Wan2GP MCP. Per dialogue line:

```
check_gpu_backend
generate_audio(mode="voice_design", text="...", instruction="...")
```

Promote MP3 from `temp/` to `audio/`.

### 4. Splice (CPU / ffmpeg)

Use full hero clips; drop only duplicate chain frames at joins (~9 s for three 49-frame clips @ 16 fps).

**CLI (recommended):**

```powershell
cd stability-studio-mcp
python scripts/storyboard/generate_storyboard.py plan --script-file beats.txt --title my_scene
python scripts/storyboard/generate_storyboard.py check
python scripts/storyboard/generate_storyboard.py splice
```

- Manifest: `<project>/logs/storyboard_manifest.json` (one file per sequence — success criteria + clip paths).
- `--project-dir` overrides `outputs.delivery` in `config.yaml`.
- `--skip-missing` on `splice` warns and skips absent clips instead of failing.

Example manifest template: `scripts/storyboard/examples/rin_manifest.example.json`.

Legacy per-beat scripts live under `scripts/storyboard/legacy/` (deprecated).

## Manifest & success criteria

| Field | Purpose |
|-------|---------|
| `success_criteria.required_clips` | Canonical MP4 paths that must exist |
| `success_criteria.final_deliverable` | Spliced output under `final/` |
| `splice.clips` | Ordered list for ffmpeg join |
| `beats[].status` | `pending` / `complete` per beat |

Run `generate_storyboard.py check` before splice; use `--strict` to fail on any missing file.

## Failure modes & limits

| Issue | Mitigation |
|-------|------------|
| ComfyUI + Wan2GP together on 16 GB | `enforce_exclusive` + `check_gpu_backend`; always `release_gpu_lock` in `finally` |
| MOSS load during hero job | Finish all `generate_video_hero` before any `generate_audio` |
| Infinitetalk truncates dialogue | Audio-driven clip length ≠ hero motion; prefer **hero splice without lipsync** for full walk/bow |
| Lip sync > ~4.5 s audio | Split lines; expect 25–60 min/clip on 16 GB |
| Character drift across beats | Chain from `*_last_frame.png`; tune negatives; same seed family per scene |
| Last frame extract fails | `extract_last_frame` falls back to middle frame |
| Hardcoded script paths | `outputs.delivery` or `--project-dir`; see `studio/storyboard_cli.py` |
| Script sprawl | Prefer `generate_storyboard.py`; legacy `_run_rin_*.py` in `scripts/storyboard/legacy/` |

## Tools map

| MCP tool | Role |
|----------|------|
| `plan_storyboard_scene` | Full pipeline plan (hero + MOSS + optional lipsync + splice) |
| `check_storyboard_readiness` | MOSS + Wan2GP + GPU + project layout |
| `plan_scene_sequence` | Draft ComfyUI I2V/V2V chain (faster, lower quality) |
| `generate_video_hero` | Production motion clips |
| `generate_audio` | Dialogue and SFX |

Future: `generate_storyboard_scene(execute=true)` — automated run of the plan (v0.4+ roadmap).
