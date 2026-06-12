# Image edit setup (IP-Adapter + ControlNet)

**Verified June 2026:** IP-Adapter SDXL + CLIP-ViT-H + depth/canny ControlNets installed; ComfyUI nodes ready. See `outputs/v2v_ip_adapter_setup.json`.

Automated via MCP — the AI should **not** ask you to run manual install steps.

**Full playbook:** [IMAGE-EDITING.md](IMAGE-EDITING.md)

## Recommended: one-shot setup

```
setup_image_editing()
```

Installs IP-Adapter, SDXL + SD 1.5 ControlNet, segmentation nodes (GroundingDINO + SAM), and flag reference PNGs (~12 GB). Restart ComfyUI when `restart_comfyui_required` is true.

Then use **`edit_image(image_path, instruction, food_group=...)`** — not manual pipeline picking.

---

## IP-Adapter (inpaint + reference objects)

### One-shot setup

```
setup_ip_adapter()
```

This will:

1. Git-clone **ComfyUI_IPAdapter_plus** (and optional ControlNet aux) into ComfyUI `custom_nodes`
2. Download **ip-adapter-plus_sdxl_vit-h** and **CLIP-ViT-H** into ComfyUI `models/`
3. Fetch bundled **Irish flag** reference (`assets/flags/ireland.png`)

**Restart ComfyUI** from Stability Matrix if any custom nodes were installed.

### Granular tools

| Tool | Purpose |
|------|---------|
| `check_ip_adapter_dependencies` | Missing ComfyUI custom nodes? |
| `install_ip_adapter_dependencies` | Git-clone IP-Adapter + ControlNet aux packs |
| `check_ip_adapter_assets` | Missing model files on disk? |
| `download_ip_adapter_assets` | Download models + flag reference |
| `setup_ip_adapter` | All of the above in one call |

`get_generation_context` includes `ip_adapter_readiness` and `ip_adapter_dependencies`.

### Using `inpaint_advanced`

Best for **adding objects** (flags, signs) in a **small** masked region:

```
inpaint_advanced(
  image_path="...templar.png",
  prompt="small Irish tricolor flag (green white orange vertical stripes) on stone church wall",
  flag_reference="ireland",
  mask_region="right_building",
  style="juggernaut",
  denoising_strength=1.0,
  ipadapter_weight=0.85
)
```

| Parameter | Notes |
|-----------|--------|
| `flag_reference="ireland"` | Bundled tricolor — no manual image hunt |
| `mask_region="right_building"` | **Preferred** for flag on right church wall |
| `mask_region="top"` | Aliased to `church_tower` — can blur/shift large background areas |
| `reference_image_path` | Override flag with your own reference photo |
| `use_controlnet_depth=True` | Optional; needs depth ControlNet + aux nodes (**SDXL only**) |

**Architecture:** IP-Adapter assets are **SDXL**. Do not use with `photorealistic` (`cyberrealistic_final` is SD 1.5). Use `juggernaut` or `photorealistic_pony`.

---

## ControlNet depth + canny (composition-guided T2I)

Locks pose, edges, and depth from a **guide image** while generating from scratch.

### One-shot setup

```
setup_controlnet()
```

Downloads **~5 GB** total:

- `controlnet-depth-sdxl-1.0.safetensors`
- `controlnet-canny-sdxl-1.0.safetensors`

Installs **comfyui_controlnet_aux** (`DepthAnythingPreprocessor`). **Restart ComfyUI** after install.

### Tools

| Tool | Purpose |
|------|---------|
| `setup_controlnet` | Install nodes + download both ControlNets |
| `check_controlnet_dependencies` | Canny, DepthAnything, ControlNet nodes |
| `check_controlnet_assets` / `download_controlnet_assets` | Model files on disk |
| `generate_image_controlnet` | T2I from guide + depth + canny maps |

### Example

```
generate_image_controlnet(
  guide_image_path="...templar.png",
  prompt="... same composition, small Irish flag on right church wall ...",
  style="juggernaut",
  depth_strength=0.52,
  canny_strength=0.65
)
```

**SDXL styles only.** `photorealistic` (SD 1.5) fails with `y is None… SDXL on SD1`.

ControlNet locks layout well but **does not reliably add** small new objects — combine with `inpaint_advanced` on `right_building` for flags.

---

## Model locations (ComfyUI package)

| File | Folder |
|------|--------|
| `ip-adapter-plus_sdxl_vit-h.safetensors` | `models/ipadapter/` |
| `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | `models/clip_vision/` |
| `controlnet-depth-sdxl-1.0.safetensors` | `models/controlnet/` |
| `controlnet-canny-sdxl-1.0.safetensors` | `models/controlnet/` |

Bundled references: `stability-studio-mcp/assets/flags/ireland.png`

---

## Recommended hybrid (hard edits)

For “keep subject + add prop” (validated on Templar + Irish flag task):

1. `generate_image_controlnet` **or** keep original as base
2. `inpaint_advanced` with `mask_region="right_building"` + `flag_reference="ireland"`
3. Compare outputs; avoid high global i2i denoise to “force” the flag

See [IMAGE-EDITING.md](IMAGE-EDITING.md) for full lessons learned.
