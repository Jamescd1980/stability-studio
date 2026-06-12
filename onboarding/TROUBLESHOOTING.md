# Troubleshooting — for agents helping non-technical users

Plain language first; technical detail in parentheses.

---

## MCP not connected / no tools

**User sees:** Agent can’t generate; “tool not found”.

**Fix:**
1. Open repo root `studio-agent/` as Cursor workspace (not parent folder).
2. Settings → MCP → `stability-studio` enabled.
3. Run `install.ps1`; `config.yaml` exists.
4. Restart MCP server or start a **new chat**.

---

## ComfyUI not running

**User sees:** `check_backends` fails; connection refused.

**Fix:** Launch ComfyUI from Stability Matrix. Wait until the web UI loads in browser.

---

## Missing custom node

**User sees:** Error names a node type (e.g. `WanVideo`, `MossTTS`).

**Fix:**
1. `check_comfyui_dependencies(workflow_id=...)`
2. `install_comfyui_dependencies` if offered
3. **Restart ComfyUI** from Stability Matrix (required)

---

## Out of memory (OOM) / ComfyUI died mid-job

**User sees:** Connection lost; black screen; `vram_free_gb: 0`.

**Fix:**
1. Only **one** video or hero job at a time on 16 GB.
2. Stop Wan2GP before ComfyUI (or the reverse).
3. Restart ComfyUI to free VRAM.
4. Lower `num_frames`; use smoke test (17 frames) before max.

---

## ComfyUI and Wan2GP fighting (16 GB)

**User sees:** `gpu_backend_conflict`; lock held.

**Fix:**
1. `check_gpu_backend` — read `blocks` and `recommendation`.
2. Finish or stop the other app.
3. `release_gpu_lock` if stale.
4. Explain: on small VRAM, **never** run both at once.

---

## Video saves but no MP4 / wrong format

**Fix:** Set environment variable `VHS_USE_IMAGEIO_FFMPEG=1` **before** starting ComfyUI (Stability Matrix package settings). Restart ComfyUI.

---

## Models missing

**User sees:** `check_wan_assets` or `check_style_assets` lists missing files.

**Fix:**
1. Run the matching `download_*` tool.
2. Large downloads — warn user (minutes to hours).
3. **Restart ComfyUI** after download.

---

## MOSS audio fails

**Fix:**
1. `check_moss_assets` — nodes + models.
2. Stop Wan2GP; ComfyUI only for `generate_audio`.
3. `check_gpu_backend` before audio on 16 GB.

---

## Hardcoded paths / files in wrong place

**Fix:**
1. Set `outputs.delivery` in `config.yaml` to project root.
2. Use folder layout from `onboarding/PROJECT.template/`.
3. Wan2GP raw files go to `temp/`; promote one canonical file to `clips/`.

---

## User only wants to see a finished example

**No GPU needed:** Open `onboarding/examples/rin/README.md` — Rin zip is a completed storyboard reference.

---

## When to escalate tier down

| Symptom | Suggest |
|---------|---------|
| Repeated OOM on video | Stay Tier 1 images only for now |
| Draft video OK, user wants perfect motion | Offer Tier 4 Wan2GP with time warning |
| Lip sync cuts dialogue | Use hero clips + splice **without** Infinitetalk |
| 24 GB+ machine | Skip Wan2GP; tune ComfyUI workflows only |
