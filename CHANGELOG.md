# Changelog

## [Unreleased]

### MCP tools restored (2026-07-17)

- Restored full MCP surface (**77 → 91 tools**): Kokoro, Forge, NSFW LoRAs, action combat, `interpolate_video`, `compile_image_prompt`
- Docs: `AUDIO-KOKORO.md`, `COMFYBOX-FORGE.md`, `ACTION-COMBAT.md`, `IMAGE-LORAS.md` (placeholders only — no LAN IPs)

### Remote ComfyUI readiness (2026-07-17)

- `studio/comfy_remote_models.py` — style readiness can trust live ComfyUI model lists when the client filesystem view is incomplete
- Catalog styles added/bumped: `anime`→v170, `n4mik4`→v20, `waijfu`, `perfection_25d`, `fantasy_prime`, `homochi`, `noobai_vpred`, legacy `anime_v160` / `n4mik4_v10`
- Restored Wan I2V workflow JSON for `i2v_5b`
- Verify: `python stability-studio-mcp/scripts/dev/verify_comfybox_ready.py`

### Remote laptop generation (2026-07)

- **Jan on laptop → desktop ComfyUI** over LAN; SMB share `StudioBata` for image delivery
- `scripts/remote-laptop/` — `studio_launch.py` SM shim, SMB setup, `map_studio_share.ps1`
- `packaging/laptop-remote/INSTALL.ps1` — one-click laptop installer
- `handoff/remote-laptop/` — `LESSONS-LEARNED.md`, `GITHUB-HANDOFF.md`, `REMOTE-STATUS.md`
- Jan MCP: `toolCallTimeoutSeconds: 600`; map `Z:` by **LAN IP** (hostname UNC often fails)
- Do **not** use SM Extra Launch Arguments for `--listen` (typo `-- listen` breaks ComfyUI)

### Prompt style lookup (2026-07)

- **`get_prompt_style(style=...)`** or **`get_prompt_style(platform=illustrious|pony|flux|wan_image)`** — compact prompt grammar before writing prompts
- Prefer over full `get_generation_context` for Jan Prompt Lab; pair with `log_image_prompt`

### Storyboard spreadsheet + Jan project tools (2026-06)

- **`studio/storyboard_sheet.py`** — CSV per chapter, generation queue, Ren'Py skeleton export
- **`scripts/storyboard/manage_sheet.py`** — `init` / `check` / `queue` / `export-renpy`
- **`studio/prompt_log.py`** — `log_image_prompt`, `list_image_prompt_log` → `logs/prompt_log.jsonl`
- **`studio/project_context.py`** — `get_project_context`, session backlog for multi-agent VN work
- [STORYBOARD-SHEET.md](STORYBOARD-SHEET.md), Jan config examples under `config-examples/`

### Jan Studio Copilot (2026-06-13)

- Hardened prompt-only vs generate rules; fixed hallucinated "I generated" responses.
- MCP: checkpoint filenames now resolve to catalog style ids (`prefectPonyXL_v6` → `pony`).
- Smoke-test troubleshooting: `vlm-prompt-training/logs/2026-06-13-smoke-test-issues.md`

- **Pony:** default style `pony` now uses **Prefect Pony XL v6** (`prefectPonyXL_v6.safetensors`) — validated on this machine.
- **Removed:** official `ponyDiffusionV6XL_v6StartWithThisOne.safetensors` (poor results vs Prefect).
- **Removed:** duplicate catalog style `prefect_pony` — alias `prefect_pony` → `pony`.

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
