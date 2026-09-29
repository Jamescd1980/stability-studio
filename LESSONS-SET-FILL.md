# Lessons learned — Blender set fill + character mesh (casting couch)

Updated **2026-08-08**. Assets live on **ComfyBox Game drive** (`D:\ComfyBox Images and Videos\…` / `/mnt/game/…`). Do not park mesh turnarounds on the main-rig TheaterJobs tree.

## Verdict

| Goal | Method |
|------|--------|
| **Locked VN BG** | Pixels outside the character must **never** enter the sampler |
| **Character look** | Comfy + LoRA paints identity; Blender supplies pose/volume/mask **only if the mesh is production-grade** |
| **Reusable body** | Naked turnaround plates → image-to-3D → posable mesh in `CHAR_POSE` — **not ready for canny keepers yet** |

Full-frame `generate_image_pose_guided` at denoise **~0.88** will reinvent couch/walls every beat. OpenPose only locks the skeleton.

## Agent delivery rules (2026-08-08 — user-enforced)

1. **One final image (or one small gate set).** Do not dump overlays / canny / guides / seeded / raw / forge into `review/` or `Images/`.
2. **Look at the pixels before calling anything a candidate.** Caption summaries lie. Fail = missing hands, sticker halo, wrong scale, empty room.
3. **Hard scale gate for camWide:** character must not fill ~85%+ of frame height. Standing in front of the couch, head should read near/below couch-back height with headroom — not a giant sticker.
4. Failed probes → **Recycle Bin**, not nested archive trees.

## What failed (casting couch strip)

### Classic (still true)

1. **rembg paste onto plate** — BG locked, sticker look / lighting mismatch.
2. **Empty high-denoise inpaint** — black voids / soft oval “portal” halo.
3. **Full-frame pose fill on empty_B** — good Darkness + hands; **BG drifted hard**.
4. **Body25 sticks as “beauty”** — silhouette too thin; Comfy invents hips/bust; bad mask.
5. **Prompt over-steering figure** — stacking `thick thighs / wide hips / hourglass` + negating `skinny / slim hips` made Darkness **too thick**. Keepers used **only `large breasts`**.

### 2026-08-08 wood + LoRA strip (rejected)

6. **Clay / silhouette canny on plate** — peach blob; not a usable edge map. Flat clay hid broken mesh topology.
7. **`darkness_body_v6` “hi-detail” beauty** — 72k verts but **head/hair explodes when posed** (proximity or auto weights). Lit beauty = spike blob. Cannot drive high-detail canny until retopo / real skinning.
8. **Full-frame ControlNet on clay beauty** — paints gradient ghosts / clay leftovers, not anime.
9. **ControlNet on empty wood plate @ high depth/canny** — room locks, **character vanishes**.
10. **Soft ControlNet on empty wood** — same: empty room keepers.
11. **i2i / txt2img with room LoRA** — often **wrong character scale** (giant in frame) + sticker outline; “least bad” is not a keeper.
11b. **Room LoRA on BJ / face-close shots (2026-08-11)** — `casting_couch_IL` is trained to *draw the couch*. Stack it with a person and you get **couch soup**, plus unprompted **windows** and **beds** (`office` does not stop beds). Catalog used to say “light room LoRA + do not CN the Blender plate.” That recipe is dead. BJ lock: `plates/bj_cam_empty_plate_v6.png` (one couch, one rug, plain wall). Background = **pre-blurred** `_blur` / `_blur_heavy` as i2i seed or composite. Room LoRA **off**. Do not prompt `couch` / `office` / `bedroom` / `window`.
12. **Forge refine on bad hardlocks** — can add ghosts, missing limbs, floating props. Do not Forge-polish trash.
13. **Seeding inpaint from mediocre hardlocks** — inherits fringe / blue-room lighting; wood LoRA fights the seed.
14. **Folder spam** — overlays + canny + guides + gens in `review/` waste the user’s time. Deliver finals only.

## What works

### Darkness body (house keepers)

- Checkpoint: **`waijfu` / waijfu_alpha** (not `waijfu_house` for strip keepers)
- LoRA: `Darkness/Darkness_id_v1` (+ eyes)
- Trigger: `nbk_darkness`
- Figure tag: **`large breasts` only** in positive
- **No** thick/wide/hourglass/slim/skinny in positive **or** negative — LoRA carries the figure

Catalog: `resolve_character_loras("darkness")` → `body_prompt_rule`, `caption_helpers`, `mesh_source`.

### Casting couch room LoRA (retrain 2026-08-08 — empty only)

- Trigger: **`nbk_castingcouch`**
- File: `casting_couch_IL.safetensors`
- Weight ~0.85–0.9; stack with Darkness ID + eyes (+ outfit LoRAs) at **generate** time
- **Train empties only** (plate + crops). Never rembg/paste characters into a BG LoRA — that baked sticker + doll scale.
- Contaminated v1 (character composites) archived on LinuxBox under `output/casting_couch/archive_with_characters_*`
- Gives “same room” prior — **not** pixel-identical BG
- Gate: empty-room still first; character stack is a separate check

### BG permanence (strip / VN stills)

1. Lock empty plate: `assets/blender/sets/casting_couch/plates/camWide_empty_wood.png`  
   (archive flat-blue: `camWide_empty_B.png`)
2. Blender: solid mesh (not sticks) → silhouette mask + depth + optional OpenPose — **only after mesh passes a lit beauty gate (no head explode)**
3. Seed mask with beauty/cutout (avoid empty-mask voids)
4. **Masked inpaint** on the plate with honored `denoising_strength` (~0.55–0.72)
5. Outside mask = byte-identical BG across beats (`outside_delta == 0`)

Pose-guided full-frame fills are **character oracles**, not final VN plates.

### Masked denoise bug (fixed 2026-08-08)

`build_advanced_inpaint_workflow` used to force `denoise=1.0` whenever a mask was present. Now honors caller denoise (clamped 0.01–1.0). Restart MCP after pull.

### Darkness mesh status

| Asset | Status |
|------|--------|
| `darkness_body_v6` | Usable for **silhouette massing only** — **not** for lit beauty / canny. Head/hair topology + skinning break under pose. |
| Next mesh work | Retopo / clean hair + proper armature weights; gate with **lit** full-scene beauty before any canny pipeline. |

```
assets/Darkness/                 # ONLY character root — do not scatter
  review/                        # current approvals for the user
  mesh/                          # darkness_body_v6.* (+ older)
```

Solid maps kept: `strip_maps/solid_mesh_v6/` (silhouettes for mask prep).  
**Deleted experiments (2026-08-08):** `strip_maps/fullscene_v1`, `hi_detail_v1`, `wood_canny_v1`, review spam folders.

## Casting couch paths

| Item | Path |
|------|------|
| Set | `assets/blender/sets/casting_couch/` |
| Locked plate | `…/plates/camWide_empty_wood.png` |
| BJ empty plate (v6) | `…/plates/bj_cam_empty_plate_v6.png` |
| BJ blurred BG | `…/plates/bj_cam_empty_plate_v6_blur.png` (+ `_blur_heavy`) |
| Archive blue plate | `…/plates/camWide_empty_B.png` |
| Solid mesh maps | `…/strip_maps/solid_mesh_v6/` |
| Room LoRA | `casting_couch_IL.safetensors` / trigger `nbk_castingcouch` |
| Wired solid strip | `…/casting_couch_strip_solid.blend` |
| Pose kit | `kits/pose_solid_strip_beats.py` |
| Lessons | this file + set `README.txt` |

## Related

- `.cursor/rules/set-3d-base-ai-style.mdc`
- `.cursor/rules/darkness-body-and-mesh.mdc`
- `.cursor/rules/wan-i2v-chaining.mdc`
- `LESSONS-BLENDER-MCP.md`
- `assets/blender/KITS.md`
- `catalog.yaml` → `character_loras.darkness` + `location_loras.casting_couch`
