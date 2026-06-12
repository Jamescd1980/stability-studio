# Rin storyboard — finished reference (Tier 0 / Tier 3)

You do **not** need a GPU to **view** this example. Use it to see what a full storyboard pipeline can produce.

## What it is

A three-beat anime scene: walk → bow → lunge, with MOSS dialogue and SFX. The **final** deliverable here is a frame-spliced hero clip (`final/Rin_storyboard_spliced.mp4`). Individual hero beats are included as separate clips.

## Watch in this repo

| Item | Path |
|------|------|
| **Final splice (start here)** | [`final/Rin_storyboard_spliced.mp4`](final/Rin_storyboard_spliced.mp4) |
| Hero still (approved) | [`images/Rin_kitsune_approved.png`](images/Rin_kitsune_approved.png) |
| Hero still (blossom variant) | [`images/Kitsune_blossom_hero.png`](images/Kitsune_blossom_hero.png) |
| Clip — walk (hero I2V) | [`clips/Rin_clip1_walk_hero.mp4`](clips/Rin_clip1_walk_hero.mp4) |
| Clip — bow with petals | [`clips/Rin_clip2_bow_petals.mp4`](clips/Rin_clip2_bow_petals.mp4) |

Open the `.mp4` / `.png` files directly in GitHub (preview) or clone the repo and play locally.

## Folder layout (model for your projects)

```
source/   images/   images/chain/   assets/
clips/    audio/    temp/           logs/    final/
```

See `stability-studio-mcp/scripts/storyboard/examples/recommended_project_layout.json`.

## Reproduce it (Tier 3 — needs GPU + time)

1. [STORYBOARD-QUICKSTART.md](../../../STORYBOARD-QUICKSTART.md) in the repo root  
2. `plan_storyboard_scene` with a script like:
   ```
   walk toward camera | Greetings.
   polite bow | My name is Rin, you killed my father.
   lunge toward camera | Now prepare to die.
   ```
3. On **24 GB+**: ComfyUI `generate_video` / hero workflows — skip Wan2GP unless needed.  
4. On **16 GB**: draft in ComfyUI; optional Wan2GP for hero beats.

## Agent note

If the user only wants inspiration, stop at Tier 0 — point to `final/Rin_storyboard_spliced.mp4` above. Do not start model downloads unless they ask to build their own.
