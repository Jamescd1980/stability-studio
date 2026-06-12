# Pose & line-art control (OpenPose + hardline maps)

Guides for **structural** edits: pose, hands, fingers — without replacing the whole frame.

## OpenPose editors (custom pose + size)

Export a **pose skeleton PNG** at your target resolution (e.g. 832×480 for Rin clips):

| Editor | URL |
|--------|-----|
| **OpenPose Editor** | https://openpose-editor.vercel.app/ |
| **Open Pose Editor (Zhuyu)** | https://zhuyu1997.github.io/open-pose-editor/ |

1. Set canvas width × height to match your still or clip frame.
2. Drag body, arms, and **hand/finger** joints (enable hands in the UI).
3. Export / download the pose image (colored stick figure on dark background).
4. Use that file as `pose_image_path` with `preprocess_pose=false`.

## Hardline maps (from a photo)

The attached **white edges on black** look is a **Canny** or **anime lineart** preprocessor output — not OpenPose.

| Map id | Preprocessor | Use |
|--------|--------------|-----|
| `canny` | Canny | Hard edges (hardline) |
| `anime_lineart` | Anime Lineart | Clean anime outlines |
| `lineart` | Realistic lineart | Softer ink lines |
| `hed` | HED | Soft edge field |
| `openpose` | OpenPose | Body + face + **hands** skeleton |
| `dwpose` | DWPose | Often sharper hand keypoints |

```text
extract_control_maps(image_path="Rin_kitsune_approved.png", maps=["openpose","canny","anime_lineart"])
```

## MCP tools

| Tool | Purpose |
|------|---------|
| `check_pose_control_readiness` | Nodes + OpenPose XL2 model on disk |
| `setup_pose_control` | Install aux nodes + download **OpenPoseXL2.safetensors** (~2.5 GB) |
| `list_pose_control_options` | Preprocessor list + editor URLs |
| `extract_control_maps` | Save preview PNGs (no generation) |
| `generate_image_pose_guided` | I2i + OpenPose ControlNet |

## Rin kunai workflow (recommended)

1. `setup_pose_control()` → restart ComfyUI if needed.
2. `extract_control_maps` on `Rin_kitsune_approved.png` — inspect openpose + canny.
3. Open **openpose-editor.vercel.app** → 832×480 → pose walk with **right hand forward holding kunai grip**.
4. `generate_image_pose_guided`:
   - `image_path` = `Rin_kitsune_approved.png` (identity)
   - `pose_image_path` = exported skeleton PNG
   - `preprocess_pose=false`
   - `prompt` = Pony tags: `holding_kunai, kunai, holding_weapon, ...`
   - `style=pony`, `denoising_strength=0.32–0.40`, `openpose_strength=0.75–0.88`
   - Optional LoRA: `concept_povholding-pony-v2.safetensors` @ 0.65

## Future (tools_needed)

- **MeshGraphormer Hand Refiner** — wire-mesh hand depth + mask for finger-level inpaint
- **OpenPose + Canny stack** — dual ControlNet (pose + line lock) in one i2i pass
