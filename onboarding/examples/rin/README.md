# Rin storyboard — finished reference (Tier 0 / Tier 3)

You do **not** need a GPU to **view** this example. Use it to see what a full storyboard pipeline can produce.

## What it is

A three-beat anime scene: walk → bow → lunge, with MOSS dialogue and SFX. Final deliverable is a **frame-spliced** hero clip (no lip sync in the final — full motion preserved).

## Where to find it

If you have the project zip:

`Desktop/New Images/Rin_Storyboard_Project_Bata.zip`

After extract:

| Item | Path inside project |
|------|---------------------|
| **Watch this** | `final/Rin_storyboard_spliced.mp4` |
| Hero clips | `clips/Rin_clip1_walk.mp4`, `Rin_clip2_bow.mp4`, `clips/Rin_clip3_stab_fade.mp4` |
| Hero still | `images/Rin_kitsune_approved.png` |
| Beat manifest | `logs/storyboard_manifest.json` |
| Full handoff | `logs/rin_session_handoff.json` |

## Folder layout (model for your projects)

```
source/   images/   images/chain/   assets/
clips/    audio/    temp/           logs/    final/
```

See `logs/recommended_project_layout.json` inside the project.

## Reproduce it (Tier 3 — needs GPU + time)

1. `STORYBOARD-QUICKSTART.md` in the repo root  
2. `plan_storyboard_scene` with a script like:
   ```
   walk toward camera | Greetings.
   polite bow | My name is Rin, you killed my father.
   lunge toward camera | Now prepare to die.
   ```
3. On **24 GB+**: use ComfyUI `generate_video` / hero workflows only — skip Wan2GP unless needed.  
4. On **16 GB**: draft in ComfyUI; optional Wan2GP for hero beats.

## Agent note

If the user only wants inspiration, stop at Tier 0 — show the zip paths above. Do not start model downloads unless they ask to build their own.
