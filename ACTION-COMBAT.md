# Action combat stills — pose-first pipeline

Fight, stab, and gore **stills** fail with one-shot `generate_image` on pinup/NSFW checkpoints. Use **WAI Illustrious** (`style=anime`) + OpenPose.

**MCP:** `get_action_combat_playbook(style=anime)` · `get_prompt_style(platform=action_combat)`  
**Storyboard:** `needs_pose=true` · `style=anime`

---

## Default checkpoint

| Beat | Style | Checkpoint |
|------|-------|------------|
| **Combat / fight / stab** | **`anime`** | `waiIllustriousSDXL_v160.safetensors` (WAI Illustrious v16) |
| Dialogue / intimacy still | `ilustmix` | iLustMix (face_detail on) |
| Gritty photo combat | `juggernaut` | SDXL photoreal |

Download WAI: `download_style_assets(style="anime")` or `python scripts/download_style_checkpoint.py --style anime`

---

## Pipeline (6 steps)

```
1. get_action_combat_playbook(style=anime)
2. check_pose_control_readiness  →  setup_pose_control if needed
3. OpenPose Editor — 1216×832, TWO skeletons, striker arm to target head
4. generate_image_pose_guided(style=anime, preprocess_pose=false, face_detail=false)
5. edit_image — small mask on face/weapon (optional)
6. generate_video mode=i2v — from keyframe (video rows)
```

Unload Jan from VRAM before GPU on 16 GB.

---

## WAI / anime example (jungle knife fight)

**Positive (danbooru tags — not photo prose):**
```text
masterpiece, best quality, 2boys, face_to_face, night, jungle, tree, moonlight, dark,
dynamic_pose, fighting, holding_knife, knife, stabbing, blood, military_uniform,
camouflage, tactical_vest, helmet, action, motion_blur, cowboy_shot
```

**Negative:**
```text
lowres, bad anatomy, bad hands, solo, 1boy, standing, portrait, looking_at_viewer,
daytime, sunlight, bright, overexposed, gun, rifle, firearm, bayonet, assault_rifle,
muzzle, scope, extra_fingers, blurry_weapon
```

---

## Alternates

**Pony** (`style=pony`) — use `rating_questionable` not `rating_explicit` for violence; score_9 prefix + same action tags.

**Juggernaut** — short photo line, knife only, no guns; still needs OpenPose.

**Do not use** `ilustmix` one-shot for combat — pinup/eye bias.

---

## `generate_image_pose_guided` defaults

| Param | Value |
|-------|--------|
| `style` | **`anime`** |
| `preprocess_pose` | `false` |
| `denoising_strength` | `0.32–0.45` |
| `openpose_strength` | `0.82–0.90` |
| `width` × `height` | `1216` × `832` |
| `face_detail` | `false` |

See [POSE-CONTROL.md](POSE-CONTROL.md).

---

## Storyboard sheet

| Column | Combat rows |
|--------|-------------|
| `needs_pose` | `true` |
| `style` | **`anime`** (or `juggernaut` for photo) |
| `prompt_positive` | WAI danbooru tags (see above) |

`list_storyboard_generation_queue` → `workflow: action_combat`, forbids plain `generate_image`.

Template: `ch01_005_still` in `scripts/storyboard/examples/ch01_storyboard.template.csv`

---

## Related

- [MODEL-FAMILIES.md](MODEL-FAMILIES.md) — Civitai download for `anime`
- [STORYBOARD-SHEET.md](STORYBOARD-SHEET.md)
- [IMAGE-EDITING.md](IMAGE-EDITING.md)
