# Image editing — tools, assets, and agent playbook

Local image editing through Stability Studio MCP. Goal: get **as close as practical** to browser image chat by hiding pipeline complexity behind **`edit_image`**, correct **architecture metadata**, and the **four art food groups**.

**Related:** [AGENTS.md](AGENTS.md) · [MODEL-FAMILIES.md](MODEL-FAMILIES.md) · [IP-ADAPTER-SETUP.md](IP-ADAPTER-SETUP.md)

---

## Four art food groups

Pass `food_group=` to **`edit_image`** or pick a matching style for **`generate_image`**.

| `food_group` | Label | Default style | Also use |
|--------------|-------|---------------|----------|
| **`anime`** | Anime | `ilustmix` | `anime`, `animagine_xl` |
| **`fantasy`** | Fantasy art | `merged_dreams` | `pony` |
| **`cyberpunk`** | Cyberpunk | `n4mik4` | `juggernaut` |
| **`photoreal`** | Photorealistic | `juggernaut` | `miracle_nsfw` (Flux2) |

```text
list_art_food_groups()          # catalog + defaults
get_generation_context          # includes art_food_groups, image_editing_readiness
```

---

## Quick start (one machine)

```
setup_image_editing()
→ restart ComfyUI from Stability Matrix if restart_comfyui_required
→ restart stability-studio MCP
→ edit_image(image_path="...", instruction="...", food_group="photoreal")
```

**Downloads (~12 GB total):** IP-Adapter SDXL, SDXL ControlNet depth+canny, SD 1.5 ControlNet depth+canny, flag reference PNGs.

---

## Primary tool: `edit_image`

Single entry for agents. Classifies intent and runs the right pipeline.

```python
edit_image(
  image_path="D:/path/templar.png",
  instruction="add small Irish tricolor flag on right church wall, keep knight identical",
  food_group="photoreal",
  mode="auto",                    # auto | i2i | inpaint | controlnet | hybrid | hybrid_preserve
  segment_prompt="",              # optional: "stone church wall on the right"
  mask_region="right_building",   # fallback if segmentation unavailable
  flag_reference="ireland",       # or auto from instruction
  preserve_subject=True,
)
```

**Preview without GPU:** `plan_image_edit(instruction=..., food_group=...)`

**Response includes:** `edit_plan`, `stages`, `verification.manual_checks` (review checklist).

### Auto pipeline selection

| Intent | Pipeline | What runs |
|--------|----------|-----------|
| Mood / lighting only | `i2i` | Low denoise img2img |
| Same layout, regen | `controlnet` | Depth + canny T2I from guide |
| Add object, keep subject | `hybrid_preserve` | Segment or regional mask → `inpaint_advanced` + IP-Adapter |
| Add object, allow regen | `hybrid` | ControlNet base → inpaint |

---

## All image MCP tools

| Tool | Use |
|------|-----|
| **`edit_image`** | **Preferred** — unified edit from natural language |
| `plan_image_edit` | Dry-run pipeline plan |
| `setup_image_editing` | One-shot: nodes + all edit models + flag refs |
| `check_image_editing_readiness` | Status of IP-Adapter, ControlNet, segmentation |
| `list_art_food_groups` | Four food groups + default styles |
| `generate_image` | T2I from scratch |
| `generate_image_i2i` | Mood/color tweaks only |
| `inpaint_advanced` | Low-level: mask + IP-Adapter reference |
| `generate_image_controlnet` | Low-level: depth + canny T2I (SDXL or SD 1.5) |
| `generate_image_guided` | T2I + IP-Adapter composition lock |
| `sync_checkpoint_architectures` | Fix catalog vs on-disk checkpoint family |
| `download_sd15_controlnet_assets` | SD 1.5 ControlNet only |

---

## Architecture traps (critical)

| Style | Checkpoint | Arch | ControlNet stack |
|-------|------------|------|------------------|
| `juggernaut` | Juggernaut XL Ragnarok | sdxl | SDXL |
| `miracle_nsfw` | Flux.2 Klein | flux2_klein | No ControlNet — use inpaint/IP-Adapter on SDXL styles |
| `ilustmix` / `anime` | ilustmix / Illustrious | sdxl_anime | SDXL |
| `n4mik4` | n4mik4 IL | sdxl | SDXL |
| `merged_dreams` | Merged In Dreams | sdxl | SDXL |

`get_generation_context.checkpoint_architecture_mismatches` warns when catalog ≠ Civitai cm-info / safetensors sniff.

**IP-Adapter** is SDXL-only. Use `food_group=photoreal` with `juggernaut` (not Flux2) for flag-reference inpaint edits.

---

## Segmentation

When `segment_prompt` is set (or auto-inferred), the server runs **GroundingDINO + SAM** (via `comfyui_controlnet_aux`) to build a mask. On failure it falls back to preset regions:

| `mask_region` | Use |
|---------------|-----|
| `right_building` | Right church wall — **flags** |
| `church_tower` | Upper tower / sky |
| `none` | Custom mask via `mask_path` in `inpaint_advanced` |

---

## Bundled reference assets

| Key | File | Use |
|-----|------|-----|
| `ireland` / `ireland_flag` | `assets/flags/ireland.png` | Irish tricolor |
| `usa` | `assets/flags/usa.png` | US flag |
| `uk` | `assets/flags/uk.png` | UK flag |

---

## Prompt rules (learned)

- Flags: `green white orange vertical tricolor` — not just “Irish flag”.
- Negatives: `orange armor`, `flag on cross`, `blurry background`, `shifted ruins`.
- **I2I does not add objects.** Use `edit_image` with `hybrid_preserve` instead.
- IP-Adapter needs **small masks** + `attn_mask` (handled in `inpaint_advanced`).

---

## Lessons learned

### Techniques
1. I2I preserves subject; it does not insert flags or signs.
2. Large top masks blur backgrounds — use `right_building` or segmentation.
3. ControlNet locks composition but resists new surface detail — combine with inpaint.
4. IP-Adapter without regional mask → color bleed on armor.

### Environment
5. Restart **ComfyUI** after `setup_image_editing` installs nodes.
6. Restart **MCP** after `server.py` tool changes.
7. Launch ComfyUI via **Stability Matrix** or package `venv\Scripts\python.exe`.

### Process
8. `check_image_editing_readiness` → `plan_image_edit` → `edit_image`.
9. Read `verification.manual_checks` in the result before declaring success.

---

## Validated experiment: Templar + Irish flag (June 2026)

| Approach | Result |
|----------|--------|
| I2I | Knight preserved; no flag |
| Inpaint `right_building` + IP-Adapter | Best flag attempts |
| ControlNet T2I (`juggernaut`) | Best layout lock; weak flag |
| **`edit_image` hybrid_preserve** | Recommended path going forward |

---

## Roadmap (remaining)

| Item | Status |
|------|--------|
| Unified `edit_image` | **Done** |
| `setup_image_editing` | **Done** |
| SD 1.5 ControlNet | **Done** |
| Segmentation (GroundingDINO + SAM) | **Done** |
| Food groups in catalog | **Done** |
| Checkpoint architecture sniff | **Done** |
| Civitai cm-info sync tool | **Done** |
| Edit-native models (Flux Kontext, etc.) | Future — stub in manifest |
| Local vision model auto-QA | Future — use `verification` checklist today |

---

*Packaged with Stability Studio MCP — update when adding tools or food-group styles.*
