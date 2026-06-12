# Changelog

## [1.0.0-beta] — 2026-06-12

### Storyboard (hero sequences)

- Unified **`studio/storyboard_cli.py`** — plan, check, splice, project paths
- CLI: **`scripts/storyboard/generate_storyboard.py`** (`plan` | `check` | `status` | `splice`)
- Manifest: `<project>/logs/storyboard_manifest.json` with success criteria per sequence
- 27 legacy `_run_rin_*.py` scripts moved to **`scripts/storyboard/legacy/`**
- Example manifest: **`scripts/storyboard/examples/rin_manifest.example.json`**

### Wan2GP hero video

- **`generate_video_hero`** — Wan2GP Enhanced Lightning v2 via headless MCP (`:7867`)
- GPU policy: **`check_gpu_backend`** / **`release_gpu_lock`** — ComfyUI and Wan2GP exclusive on ≤16 GB
- Validated: 49 frames @ 832×480, ~125 s on 16 GB (Rin bow reference)

### Video (ComfyUI draft)

- Default I2V: **`i2v_5b`** (Wan 2.2 TI2V-5B) + PainterI2V motion
- Default V2V: **`v2v_5b_painter`**
- Optional video LoRAs + machine-local overlay (`wan_video_loras_local.py`)

### Docs

- [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) — Rin walk/bow/stab example (Wan2GP + MOSS + splice)
- [WAN-ASSETS.md](WAN-ASSETS.md), [AGENTS.md](AGENTS.md), [OPEN-INTERPRETER-INTEGRATION.md](OPEN-INTERPRETER-INTEGRATION.md) updated

### Packaging

- Handoff zip: **`scripts/build_handoff_zip.py`** — excludes `config.yaml`, `outputs/local/`, personal MCP paths
- **`outputs/local/`** for machine-specific test JSON/logs (gitignored)

## [0.4.0] — 2026-06-11

- MOSS-TTS audio tools, storyboard MCP planning, project delivery layout
- Wan T2V smoke test (81 frames @ 16 GB), i2v_5b draft validation
