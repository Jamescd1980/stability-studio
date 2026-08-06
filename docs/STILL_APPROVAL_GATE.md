# Still approval gate (Theater Jobs)

**Do not copy stills into `TheaterJobs/game/` until the user explicitly approves.**

## Flow

1. **Generate** — land outputs under ComfyBox Images, not the game tree:
   - Preferred: `D:\ComfyBox Images and Videos\Images\proof_queue\`
   - Also proof-only (not installed): `D:\ComfyBox Images and Videos\Images\story_stills_v1\`
2. **Orla VLM** — cheap hint only. Do **not** trust pass/fail for install decisions.
3. **Agent review** — look at pixels; say yeah / neh with brief reasons.
4. **User approves** — explicit keep / install OK.
5. **Only then** — copy into `TheaterJobs/game/images/cg/…`, register tags in `images.rpy`, and wire scene jumps in script.

## Rejected pack (2026-07-26)

User rejected the installed Girls 3some + Fern/Darkness CGs as trash quality.

- Recycled (Recycle Bin): `game/images/cg/girls_3some/`, `game/images/cg/fern_darkness/`
- Unwired: `images.rpy` CG tags; `script_saloon.rpy` aftercare jumps straight to `coming_soon`
- Proof copies (if any) stay under ComfyBox Images — never re-install without approval
