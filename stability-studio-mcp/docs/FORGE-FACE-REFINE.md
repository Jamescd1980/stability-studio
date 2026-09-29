# Forge face refine — MCP tools + Nari review

## Tools

| Tool | Role |
|------|------|
| `face_denoise_guide` | Preset table + policy |
| `detect_face_box` | Tight `[x1,y1,x2,y2]` (YOLO or heuristic) |
| `refine_face_forge` | Box → region inpaint → Nari+heuristic loop |
| `review_face_forge` | Review only (before/after) |
| `refine_image_forge` | Global polish (not face-critical) |

## Denoise (face Forge)

| Preset | Denoise | Use |
|--------|---------|-----|
| `eyes_only` | ~0.08 | Oral / eyes lock |
| `face_soft` | ~0.10 | Light clean |
| `face_refine` | ~0.15 | **Default** identity-safe |
| `face_rescue` | ~0.20 | Harder fix |
| hard cap | **0.25** | Explicit override only; never auto higher |

Include facial expression in `face_prompt` (open/closed mouth, smirk, gasp, tongue, blush).

## Eye / hair / markings lock (required)

**Before Forge:** look at the source still and note **eye color**, **hair color**, and any **tattoos / face markings** (cheek marks, glyphs, freckles, scars, facial tattoos, paint) — or explicitly that there are none. Put those in `face_prompt`. Agents must not invent, erase, or “clean off” markings.

**After Forge:** Nari fails the pass if eyes, hair, tattoos, or face markings drifted vs BEFORE. Revert — do not send identity-drift keepers to the user.

Intentional recolor / marking edit (rare): only when the user explicitly asked; that is the usual case for higher denoise, never accidental.

## Review criteria (Nari + heuristic)

**FAIL** if:
- Eye color, hair color, tattoos, or face markings changed / removed / invented vs source
- Top half looks redrawn while bottom does not match source
- Identity drift / seam halo / floating head
- Face overbake vs frozen body

**PASS** → `send_to_user: true` — only then show the human. Human still final-approves.

Heuristic always checks lower-half MSE. Nari adds semantic JSON pass/fail (includes `eye_color_match` / `hair_color_match` / `markings_match`). If Nari is down, heuristic alone soft-gates and notes the gap.

## Workflow

1. Note eye + hair color and tattoos/face markings (or none) from the source still
2. `switch_stills_backend(forge)`
3. `refine_face_forge(image_path, face_prompt=... with colors + markings + expression, preset=face_refine)`
4. If `pass` / `send_to_user` → show `saved_files[0]` + `frame_preview`
5. If fail (incl. color/marking drift) → revert; try `face_soft` / tighter box — do not stack denoise
6. `switch_stills_backend(comfy)` before video

## Config

`nari_ollama.review_model` (optional) — Ollama tag for vision review; defaults to `nari`.
