# NSFW stills — lessons (waijfu / Comfy)

Updated **2026-08-10** after Hidden BG Frieren-room facesit failures (Theater Jobs).

**Prompting law:** Do's → **positive**; Don'ts → **negative**.  
**Lexicon:** **gold standard** = `resolve_style_lane` + LoRAs/settings/prompt_tail — **never** paste into Forge/Comfy prompts. See `docs/PROMPTING.md` (doc id `prompting`).

## Prompt length

- **Short wins.** Essay prompts (stacked quality + identity packs + pose said three ways + over-detailed room) → melt, PIP, identity bleed, wrong act.
- Owner pattern: quality once → `anime++` → short night/room → `nb_fern` / `nb_frieren` + few traits → one act sentence → view.
- Negatives stay short too (anatomy + Trees + PIP + man/penis + junk). Do not dump every possible anti-tag.

## Character LoRAs

| Char | File | Weight | Notes |
|------|------|--------|--------|
| Fern | `Fern/Fern_id_v1.safetensors` | ~0.8–0.9 | Use id_v1 (identity, not style drift). Trigger `nb_fern`. |
| Frieren | `Frieren/Frieren_id_v1.safetensors` | **≤ 0.50** or omit | **Built into waijfu_alpha.** High weight → dual-Frieren / both elves. Trigger `nb_frieren` still in prompt. |
| Eyes / detail / night | Eyes ~0.75, ILDetailerV2 ~0.65, S1 ~0.6, Darkness_sliderFin3 ~0.55 | Gold finish stack | `resolve_style_lane("gold standard…")` → `illustrious_detail_hero` |

## Pose LoRAs

- Local `povFacesitting.safetensors` is **Pony** — **do not** stack on waijfu (deforms). Prefer prompt-only facesit or an Illustrious facesit LoRA if/when installed.

## Dual-girl hard contact (facesit / 69)

- Free t2i of dual-face contact repeatedly failed (melt, wrong pose, PIP) even with short prompt + Frieren@0.45.
- Prefer: **i2i from a good original** (short prompt, low denoise) for room-only changes, or **one-face** facesit recipe (Fern ID only; under face described lightly) — see Wild Fern gold lessons.
- Bad BG masks (window/curtain inpaint) will paint over characters — do not “fix room” that way without a clean body lock.

## PIP

- User hates picture-in-picture / inset panels. Negate: `picture in picture, inset, panel, comic panel, collage, border, frame, stickers, pop art, manga`.

## Misty / Shooting Gallery (waijfu, 2026-08-17)

No character LoRA. No eye LoRAs. FaceDetailer **off**. Micro-shorts LoRA only while shorts are on.

**Layer order (owner):** quality → stage (beach) → lighting (sunny day) → person(s) → one action sentence → sex-act tags → view (`side view, profile` or `Man's POV, view from above`). Never say camera.

Identity: `Misty with solid orange hair, orange bangs, and short side ponytail with blue hair tie, aqua eyes`. Never `white skin` / `pale` in positive. `Black skin, Brown skin` in negative only.

Keep negs short. Long anti-lists melted oral. Star pupils and multi-colored hair are auto-fails (owner will not inpaint). Look-up + `blue hair tie` paints teal bangs — add `orange bangs` in pos and `two-tone hair` in neg.

Facial is not oral: drop suck / deepthroat / throat bulge. Use `a large thick cock in front of her face shooting cum on her` + `Cum shot, sticky cum, facial`. Do not prompt nose-cum (it appears from oral creampie anyway).

Vaginal (Stage 3): `Man's POV, view from above`. Bury with `buried in her pussy` + `vaginal penetration`. Rough = `legs in the air, legs on his shoulders` + `mating press` — not `legs over her head` (pulls BJ). Cum on pussy needs `pulled out shooting cum on her pussy`; negate oral / kneeling / facial or look-up snaps back to Stage 2.

Forge (owner): every pass needs an **objective**. Describe the scene in img2img **and** AD or it pulls cock out / strips cum. Face pass separate from cum pass. Masters in `Originals\`; drop `*_forge.png` in the same Stage folder. img2img 0.05–0.06 + AD face 0.10–0.14. Adding **new** cum onto a clean still at safe denoise barely paints; boosting existing cum works.

Full session notes: `D:\Bad boy\TheaterJobs\LESSONS_LEARNED.md` (2026-08-17 Misty beach stills).

## Jessie / Shooting Gallery (waijfu, 2026-08-17)

LoRA `Jessie/jessie_pokemon_illust.safetensors` @ 0.8. Trigger `jessie (pokemon)`. Jungle theme. Owner hair: **dark magenta / dark pink, loose natural, not slicked back** — do not copy catalog `hair slicked back`. Skip Civitai `red lips`. Outfit: `team rocket uniform, white crop top, black undershirt, black elbow gloves, white skirt, black thighhighs, green earrings`. Reverse cowgirl needs lookback or the pleasure face is gone. Anal cowgirl = facing viewer — never `view from below` (snaps to reverse). Negate `heart-shaped pupils`. No fluids unless asked.

**Eyes (2026-08-18):** one `face_yolov8n` pass from the original (img2img 0.05 / AD 0.10–0.14). Never stack a second “eye pass” on Jessie. Never Mediapipe / Anzhc Eyes. Never put `purple eyes` / `teal eyes` / `cyan eyes` in neg (they pull the color). Never put earrings in the AD face prompt. Dirty source irises → new still, not more Forge.

Full notes: `D:\Bad boy\TheaterJobs\LESSONS_LEARNED.md` (2026-08-17 Jessie jungle; 2026-08-18 menu / ship).

## Cross-links

- `.cursor/rules/nsfw-sex-prompting.mdc`
- `D:\Bad boy\TheaterJobs\LESSONS_LEARNED.md` (2026-08-10 Hidden BG; 2026-08-17 Misty beach; 2026-08-17 Jessie jungle; 2026-08-18 gallery ship / Jessie eyes)
- `docs/invoke_nsfw_prompt_examples.md`
- `docs/character_id_lora_retrain_v1.md`

### Touch-up labor (2026-09-22)

- Prefer Krita on Orla for hand touch-ups / custom painting AI fails at. Do not spin local Invoke for that while ComfyBox GPU sits idle. AI inpaint/refine that needs diffusion → ComfyBox (Forge/Comfy) or Krita AI Diffusion pointed at ComfyBox. Invoke outputs may stay archival masters; live touch-up path is Krita + ComfyBox, not Invoke on the 5060.  
<!-- appended 2026-09-22 via append_lesson -->

### edit_image routing

- edit_image auto must never fall back to demo masks church_tower/right_building. Face/eyes/hair/tattoo/marking asks → i2i + face_detail (or refine_face_forge). Hybrid needs an explicit mask_region/segment_prompt; defaults denoise≈0.45 IP-Adapter≈0.55 (not 1.0/0.85).  
<!-- appended 2026-09-28 via append_lesson -->

### edit_image Forge face route

- Face edits: edit_image now auto-routes to refine_face_forge (Forge YOLO box + region inpaint). Never hybrid_preserve/right_building/church_tower for faces. Prefer refine_face_forge directly; keywords face/eyes/hair/tattoo/markings. Restart MCP after studio code changes.  
<!-- appended 2026-09-28 via append_lesson -->
