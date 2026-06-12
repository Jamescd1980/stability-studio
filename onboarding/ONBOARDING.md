# Stability Studio — agent onboarding playbook

**Audience:** AI assistants (Cursor, Open Interpreter) guiding a less technical user.  
**Not a one-stop installer** — this MCP exposes ComfyUI and related tools through conversation.

Read **`CHECKLIST.yaml`** for machine-readable tiers, tools, and VRAM rules.

---

## Your job as the agent

1. **Be honest early** — large downloads, NVIDIA GPU, restarts are normal.
2. **Ask 2–4 questions**, then act — don’t interrogate.
3. **Pick the lowest tier** that meets the user’s goal; gate higher tiers.
4. **Run checks before generating** — `get_generation_context`, `check_backends`, tier-specific `check_*`.
5. **One first win** — small image or 17-frame video before max quality.
6. **Defer Wan2GP** unless the checklist says to offer it.

---

## Opening questions (pick what you still need)

| # | Question | Maps to |
|---|----------|---------|
| 1 | What do you want to make? (images / short clip / full scene / just see an example) | Tier 0–3 |
| 2 | Do you have an NVIDIA GPU? (rough VRAM if they know) | VRAM routing |
| 3 | Is Stability Matrix or ComfyUI already installed? | Skip or deep install |
| 4 | What look do you want? (anime, fantasy, realistic, cyberpunk) | `food_group` / style |

After answers, call **`get_onboarding_context`** (if MCP connected) or read `CHECKLIST.yaml` + `get_generation_context`.

---

## VRAM routing (important)

| VRAM | Default | Wan2GP |
|------|---------|--------|
| **≥ 24 GB** | ComfyUI only for images + video | **Do not offer** unless user hits a specific wall |
| **16–23 GB** | ComfyUI; draft video via `i2v_5b` | Offer only if user wants **best** motion/lip sync and accepts stopping ComfyUI |
| **≤ 16 GB** | ComfyUI images + draft video | Same — Wan2GP is **optional advanced**, not default |

On 24 GB+, simplify the story: *one program (ComfyUI), one workflow.*

---

## Tier guide

### Tier 0 — Browse (no GPU)

- Point to **`examples/rin/README.md`** and the Rin zip (finished storyboard).
- Explain what tiers 1–3 unlock.
- Do not run installs until they choose a goal.

### Tier 1 — Still images

**Programs:** Stability Matrix, ComfyUI, this MCP.

1. `install.ps1` → edit `config.yaml` from `onboarding/config.yaml.template`
2. Launch ComfyUI; enable MCP in Cursor
3. `get_generation_context` → `check_backends`
4. `check_style_assets` / download if Flux2 or missing checkpoints
5. **First win:** `generate_image` — anime portrait, modest size

**Edits:** `setup_image_editing()` once → `edit_image` with `food_group`.

### Tier 2 — Draft video

**Requires:** Tier 1 working.

1. `check_gpu_backend` → `check_comfyui_dependencies(workflow_id="i2v_5b")`
2. `check_wan_assets` → `download_wan_assets` if needed → **restart ComfyUI**
3. Set `VHS_USE_IMAGEIO_FFMPEG=1` before ComfyUI if MP4 fails
4. **First win:** `generate_video` — 17 frames, `i2v_5b` or `t2v` smoke test

Do **not** mention Wan2GP yet.

### Tier 3 — Storyboard

**Requires:** Tier 2 + MOSS for dialogue.

1. `check_storyboard_readiness`
2. Copy **`PROJECT.template/`** to user’s project folder; set `outputs.delivery`
3. `plan_storyboard_scene` with their script (`action | dialogue` lines)
4. Per beat: `generate_video_hero` **or** ComfyUI `generate_video` on 24 GB
5. MOSS `generate_audio` for lines (ComfyUI only — stop Wan2GP first on 16 GB)
6. ffmpeg splice — see `STORYBOARD-QUICKSTART.md`

Reference: Rin sequence in `examples/rin/`.

### Tier 4 — Hero / lip sync (opt-in only)

**Only when:** user explicitly wants best motion or talking head **and** accepts complexity.

1. Warn: stop ComfyUI; long renders; 16 GB = one backend at a time
2. `check_gpu_backend` → `check_wan2gp_runtime` → `generate_video_hero`
3. Lip sync (Infinitetalk): even slower — suggest hero splice without lipsync on tight VRAM

---

## Project folder (Tier 3+)

Copy `onboarding/PROJECT.template/` and set `outputs.delivery` to that path:

```
MyProject/
  source/  images/  images/chain/  assets/  clips/  audio/
  temp/    logs/    final/         rejected/
```

- **`assets/`** — canny, lineart, openpose only  
- **`temp/`** — raw saves until user approves  
- **`logs/`** — JSON only  

See `outputs/recommended_project_layout.json`.

---

## Programs checklist (tell the user plainly)

| Program | When needed |
|---------|-------------|
| Cursor or Open Interpreter | Always |
| Stability Matrix + ComfyUI | Tier 1+ |
| Wan models in ComfyUI | Tier 2+ |
| MOSS-TTS in ComfyUI | Tier 3 dialogue |
| Wan2GP | Tier 4 only, mainly ≤16 GB hero path |
| ffmpeg | Tier 3 splice (usually already present) |

---

## When things fail

See **`TROUBLESHOOTING.md`**. Default fixes:

- Missing node → `install_comfyui_dependencies` → restart ComfyUI  
- OOM / connection lost → one GPU job; restart ComfyUI  
- MCP tools missing → restart Cursor MCP; new chat  
- Wan2GP + ComfyUI conflict → `check_gpu_backend`; `release_gpu_lock`  

---

## MCP tools for onboarding

| Tool | When |
|------|------|
| `get_onboarding_context` | Start of session — tiers + VRAM advice + checklist |
| `get_generation_context` | Before any generation |
| `check_backends` | ComfyUI up? |
| `check_gpu_backend` | Before video, audio, hero |
| `check_storyboard_readiness` | Tier 3 |
| `plan_storyboard_scene` | Tier 3 plan (no GPU) |

---

## Tone

- Short sentences. No jargon without a one-line explanation.  
- Celebrate the first successful image.  
- Never promise “one click” — promise *“I’ll run the checks and tell you the next step.”*
