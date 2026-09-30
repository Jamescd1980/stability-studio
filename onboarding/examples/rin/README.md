# Rin storyboard — finished reference (Tier 0 / Tier 3)

You do **not** need a GPU to **view** this example. Use it to see what a storyboard pipeline can produce.

## What it is

A short anime scene made with this MCP: Rin walks toward the viewer, bows with falling petals, then lunges. The **final** clip (`final/Rin_storyboard_spliced.mp4`) is the three beats frame-spliced together. The walk and the bow are also included as separate clips; the lunge exists only inside the final.

**There is no sound.** None of the clips has an audio track, and no dialogue or sound-effect files are included.

## What's in this folder

| Item | Path | Details |
|------|------|---------|
| **Final splice (start here)** | [`final/Rin_storyboard_spliced.mp4`](final/Rin_storyboard_spliced.mp4) | Walk → bow → lunge, 118 frames at 16 fps (7.4 s), 480×704, no audio |
| Clip — walk (hero I2V) | [`clips/Rin_clip1_walk_hero.mp4`](clips/Rin_clip1_walk_hero.mp4) | 49 frames at 16 fps (3.1 s), 528×768, no audio |
| Clip — bow with petals | [`clips/Rin_clip2_bow_petals.mp4`](clips/Rin_clip2_bow_petals.mp4) | 49 frames at 16 fps (3.1 s), 512×656, no audio |
| Hero still (approved) | [`images/Rin_kitsune_approved.png`](images/Rin_kitsune_approved.png) | Source still |
| Hero still (blossom variant) | [`images/Kitsune_blossom_hero.png`](images/Kitsune_blossom_hero.png) | Source still |

Open the `.mp4` / `.png` files directly in GitHub (preview) or clone the repo and play locally.

## Coming next

A simpler teaser rebuilt from the bow: breeze and footsteps, with a Japanese "hello" on the bow (Kokoro voice). It will replace the "no sound" note above when it lands.

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
   walk toward the viewer | Greetings.
   polite bow | My name is Rin, you killed my father.
   lunge toward the viewer | Now prepare to die.
   ```
   The dialogue lines are for planning; this example was delivered without the voice track.
3. On **24 GB+**: ComfyUI `generate_video` / hero workflows — skip Wan2GP unless needed.
4. On **16 GB**: draft in ComfyUI; optional Wan2GP for hero beats.

## Agent note

If the user only wants inspiration, stop at Tier 0 — point to `final/Rin_storyboard_spliced.mp4` above. Do not start model downloads unless they ask to build their own. Don't describe this example as having dialogue or sound effects.
