# Lighting agents — Theater Jobs / Galleria

**Path:** `D:\studio-agent\docs\LIGHTING-AGENTS.md`  
**Audience:** Cursor / Stability Studio / any merge or stills agent  
**Related:** [`HOUSE-CHECKPOINT-PLAN.md`](HOUSE-CHECKPOINT-PLAN.md), [`MERGE-WAIJFU-REEDXXX-phase0.md`](MERGE-WAIJFU-REEDXXX-phase0.md), catalog `lighting_sliders` / `waijfu_house*`, `.cursor/rules` (NSFW prompting, set-fill, scene-checkpoint-routing)

This file is the **lighting + house-ckpt** instruction surface. Outfit logic, Wan I2V, and media delivery stay in their own rules — do not duplicate them here.

---

## Kill list (must not invent)

| Failure | What it looks like |
|---|---|
| Invented windows / lamps / sun | Unprompted bright windows, skylights, floor lamps, sunbeams, outside trees |
| Nuke-sun interiors | Flat overbright rooms; blown highlights; “daylight” wash indoors |
| S1 silhouette halo | Bright rim / plastic outline around the body after heavy Dramatic Lighting bake |
| Lens flares / light leaks | Streaks, prism blobs, anamorphic flares, orange/cyan leaks |
| Cross / star catchlights in eyes | Plus-sign, cross, or hard star glints in the iris (not soft round catchlights) |
| Locked-plate BG reinvent | New architecture when filling onto a locked Blender / set plate |

Lighting knobs exist to **kill** these — not to add more “cinematic” sources.

### Eye / flare negatives (add when those show up)

```
lens flare, light leak, anamorphic flare, optical flare, cross-shaped pupils,
star pupils, plus-shaped catchlight, glowing eyes, overbright eyes
```

Do **not** stack `LensFlare_LightLeak_IL`, `ZH_GlowEyes_IL`, or high `S1 Dramatic Lighting` when chasing the soft baseline look.

---

## Good tags (prefer)

- Mood: `dim room`, `soft lighting`, `soft key light`, `single practical light`, `night time` when the beat is night
- Framing (sex / POV): `View from mans POV` — **never** the word `camera` (spawns props)
- Quality / style layers already house-standard: short Invoke-style stacks (`masterpiece, best quality, anime++, bold outline, cel-shaded coloring`) — see NSFW prompting rules
- Closed rooms: plain walls, leather couch edge, wood floor — let plate / room LoRA carry set ID

---

## Bad tags (avoid unless the beat explicitly asks)

| Avoid | Why |
|---|---|
| `cinematic lighting` spam | Vague; often invents extra sources |
| `volumetric rays` / god-rays | Window + sun invent |
| `bright window`, unprompted `lamp` / `floor lamp` | Direct invent triggers |
| `cum`, `fluid`, `fluids`, `semen`, `ejaculate`, `discharge` | Pull male semen / splatters — use `wet pussy` / `pussy juice` only for female wetness (NSFW fluids policy) |
| Essay lighting locks on Wan I2V | Melts faces; motion-only prompts |

Useful negatives when killing invent-light (do not paste blindly into every scene):  
`window, windows, skylight, bright window, daylight, sunlight, sunbeam, trees, outside view, overexposed, blown highlights, floor lamp clutter, picture in picture, panels, collage`

---

## House checkpoint status (review)

Gold paint bar = bare **`waijfu` / `waijfu_alpha`**. Reedxxx = stronger contact, more generic anime finish (Phase 0). Both parents invent windows/lamps — merge does not fix that alone.

| Version | Recipe (bake into waijfu) | Role / known issue |
|---|---|---|
| `waijfu_house_v1` | S1@0.7 + `anti_sprawl`@0.75 | Legacy — **silhouette halo**; avoid for strip keepers |
| `waijfu_house_v2` | `house_pref`@0.7 | Soft house stills; A/B keep |
| `waijfu_house_v3` | `house_pref`@1.0 (no S1) | PIP-hard; no lighting bake |
| **`waijfu_house_v4`** | `house_pref`@1.0 + `anti_sprawl`@0.45 + **S1@0.28** | **Demoted 2026-08-11** — giant window inversion in Invoke |

### v4 — do not use (owner + Invoke review 2026-08-11)

**Windows got worse, not better.** Three Invoke stills on `waijfu_house_v4` + Darkness@0.6 + **S1@0.55 again** + `windows` in the negative all spawned a huge night-city window (office monitor / wall hole). The anti_sprawl bake inverted: the model treats “window” as a thing to draw large.

Also: gold finish already reported as generic/Reed-ish; S1 double-stack (bake + runtime) fights dim; `office` in the prompt invites glass.

**Use instead:**
- Sex / gold paint: **`waijfu_alpha`**
- PIP-hard closed room: **`waijfu_house_v3`** (pref only, no S1 / no extra asprawl bake)
- Windows at runtime: `house_pref_IL` ~0.65 — do **not** bake more anti_sprawl, do **not** put `windows` in the negative (say `plain walls, closed room` in positive)
- Do **not** stack S1 on any house bake

Catalog `waijfu_house` now points at **v3**.

---

## LoRA rules

### Cast identity (runtime only — never bake)

Use `resolve_character_loras(character=…)` when ID is required. Put the **trigger in the positive prompt**.

| Character | File (prefer) | Trigger | Notes |
|---|---|---|---|
| Frieren | `Frieren/Frieren_id_v1.safetensors` | `nb_frieren` | Cap ≤ **0.50** on waijfu (overbaked risk) |
| Fern | `Fern/Fern_id_v1.safetensors` | `nb_fern` | Prefer **0.55–0.70** when lighting matters (0.8 fights dim) |
| Darkness | `Darkness/Darkness_id_v1.safetensors` | `nbk_darkness` | Figure: **`large breasts` only** — no thick/wide/hourglass |

**Owner-confirmed — character LoRAs vs lighting (2026-08-10):**  
Cast ID LoRAs **override lighting prompts and lighting LoRAs** (pinup gloss / bright paint from training). They win the lighting fight more often than dim tags or room LoRAs.

| Do | Don't |
|---|---|
| Drop or lower cast ID when chasing dim / baseline lighting | Stack Fern/Frieren/Darkness @0.8–1.0 and expect Darkness slider / dim tags to win |
| Lock lighting on bare `waijfu` first, then light ID i2i / low-weight ID | Assume `soft lighting` in the prompt beats the ID LoRA |
| Cap Frieren ≤0.50; try Fern/Darkness ≤0.65 for lit scenes | Blame only S1 / house v4 when ID is on the graph |

### Lighting / room (runtime preferred)

| LoRA | Trigger / use | Bake? |
|---|---|---|
| `Darkness_sliderFin3` / `Darkness-sliderFin3` | Dim on **ComfyUI / agent** graphs @ +0.4–1.2 | **Never bake** |
| `Darkness_Slider2` | Alt dim (Comfy) | Never bake |
| `S1_Dramatic_Lighting_Illustrious_V2` | Runtime when needed | **Do not bake** into sex house (halo); v4 already has mild S1 |
| `anti_sprawl_IL` | Anti window/lamp invent | Bake light only in deliberate `…_vN` house forks |
| `house_pref_IL` | Trigger `housepref` ~0.65–0.85 | Same — prefer runtime if v4 finish is muddy |
| `casting_couch_IL` | Trigger `nbk_castingcouch` — **empty room only** | Never bake into sex ckpt |

**Darkness slider — Invoke (owner-confirmed):**  
Does **not** work reliably in Invoke (slider was built / validated for **ComfyUI** weight application). File may load in Invoke (`Darkness-sliderFin3`) but dimming does not behave. On Invoke: use **prompt dim tags** + bare/`waijfu_house_v3` + lower cast ID. Use the slider on ComfyBox agent gens only.

**Casting couch room LoRA — Invoke (owner-confirmed):**  
`casting_couch_IL` / `nbk_castingcouch` **deforms the character** when stacked with a person in-frame — especially **fingers and feet**. Train intent was **empty room**.  

**BJ / close-up (owner 2026-08-11):** room LoRA **OFF**. Stacking it redraws the couch on every brown patch (couch soup), plus windows and beds. `office` does not kill beds — it adds glass. Locked BJ plate: `plates/bj_cam_empty_plate_v6.png` + `_blur` / `_blur_heavy`. Guidance = the blurred plate (i2i seed or composite), not the room LoRA. Prompt `blurry background, depth of field, simple background, plain wall`. Never `couch` / `office` / `bedroom` / `window`.

| Do | Don't |
|---|---|
| Empty BG / plate gens only; composite character on locked plate | Stack casting_couch @0.7–1.0 with cast ID for full-body keepers |
| BJ: room LoRA off; i2i / composite on `bj_cam_empty_plate_v6_blur.png` | Treat casting_couch as a “set dressing” LoRA on strip / BJ / standing shots |
| If you must hint the wide room with a character: weight **≤0.30–0.40** and expect hand/foot cleanup | Use casting_couch to “fix” lighting or “keep the room” |

### Scene routing (pointer)

Sex/NSFW contact → `waijfu` lane. Dialogue/face → `ilustmix`. Pose-heavy → `anime` / `noobai_vpred`. Empty set plates → Blender plate / not sex ckpt. See scene-checkpoint-routing rule.

---

## Safety (checkpoints + delivery)

1. **Never overwrite** `waijfu_alpha.safetensors`, `reedXXXIllustrious_v150.safetensors`, or other donor bases.
2. Merges / bakes write only new names: `waijfu_house_vN.safetensors` (or dated experiment stems) under ComfyBox SM / merge output — never in-place replace.
3. **Owner keepers** → `D:\Extra Models\Waifu\` (Forge / Invoke). LoRAs → `D:\Extra Models\` or `LoRa's\`.
4. ComfyBox Stability Matrix paths = **agent gens only** — do not treat local Windows SM ComfyUI as the owner install.
5. Backup before any bake: copy the parent ckpt to a dated archive path if you are unsure the tool writes a new file.
6. Rejected candidate ckpts → Recycle Bin (no hard-delete); do not leave 0-byte stubs as “installed.”

---

## LoRA inventory note (Invoke + ComfyBox)

Lighting / flare / eye LoRAs exist on **both** machines because the bright/flare problem already existed — they are **remedies on disk**, not proof the owner is stacking them in Invoke.

**Owner:** not running S1 / LensFlare / GlowEyes in Invoke for house work.  
**Agent images:** eye crosses / flares are introduced in **our** pipeline (see Forge section below).

### Same LoRAs on ComfyBox SM

Path: `/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/` (also mirrored under Invoke UUID folders).

| File | Role |
|---|---|
| `S1_Dramatic_Lighting_Illustrious_V2.safetensors` | Dramatic / bright key (also baked mild into house v4) |
| `LensFlare_LightLeak_IL.safetensors` | Flares / light leaks |
| `DramaticColor_IL_v1.safetensors` | Hotter color contrast |
| `Darkness_sliderFin3.safetensors` / `Darkness-sliderFin3` / `Darkness_Slider2` | Dim slider (negative weight brightens) |
| `Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors` | Default eye LoRA (`perfect eyes`) — hard catchlights |
| `ZH_GlowEyes_IL.safetensors` | Glow eyes |
| `Dlang_DetailedEyes_IL.safetensors` / `Loraeyes_V1.safetensors` | Extra eye detail |
| `ILDetailerV2.safetensors` / `hinaTuningFaceDetailer_…` / `hyperdetailer_v095` | Face/detail punch |

Do **not** auto-stack S1 / LensFlare / GlowEyes on agent gens. Catalog `illustrious_detail_hero` listing LensFlare @0.35 is optional recreate junk — not Galleria default.

---

## Why ComfyBox baseline looked softer than Invoke (character LoRAs)

**Fact:** Invoke `Fern_id_v1` / `Frieren_id_v1` / `Darkness_id_v1` **byte-match** ComfyBox SM copies (same MD5). Not a different LoRA on the box.

**What made the baseline pack look different:**

| Knob | Soft baseline pack | Typical owner / agent cast gen |
|---|---|---|
| Character ID LoRA | **None** | Fern / Frieren / Darkness @ ~0.8 |
| Eyes LoRA | None | Often `Eyes_for…` + `perfect eyes` |
| Lighting tags | Explicit `dim room`, `soft key`, `single practical` | Often missing or `cinematic` / bright room |
| Checkpoint | bare `waijfu` / house / runtime slider | Often `waijfu_house` (v4 = mild S1 bake) |
| Forge ADetailer | Not used | Often on → eye flares |

**Character LoRA check (training):**
- Sources: Grimoire (Fern/Frieren) + Konosuba (Darkness) pinups — mid-bright paint (sample mean luma ~117–133), glossy pinup look.
- Captions almost all stamp `soft lighting`, but **pixels** still carry bright specular / outdoor / night-sky lantern looks (Fern captions include `outdoors`, `sky`, `window`, `lantern` on some rows).
- Retrain doc warned: identity-only captions that skip describing style **absorb pinup gloss into the LoRA**. These IDs can push brighter, shinier skin even when you want dim rooms.
- Frieren is also **baked into waijfu_alpha** — stacking `Frieren_id` high (catalog 0.8; house plan says ≤**0.50**) amplifies punch/gloss.

**So:** soft ComfyBox look ≠ secret lighting LoRA. It was **no cast ID + dim tags + no Forge eyes pass**. Character IDs are the same files; they pull training-set gloss when stacked at high weight.

**Invoke A/B to confirm:** same seed/prompt, bare `waijfu_alpha` vs +`Fern_id`@0.8 vs +`Fern_id`@0.5 — if brightness jumps with the ID, the LoRA is carrying gloss.

---

## Root cause: eye flares on agent / Forge images

**Symptom:** Cross / star / sparkle catchlights appear (or get worse) after Forge refine — not from the owner’s Invoke LoRA stack.

**Mechanism:**
1. `refine_image_forge` defaults **`adetailer=True`** (`studio/forge_backend.py`) with face YOLO and a weak default ad negative (`blurry face…` only). ADetailer re-inpaints the face and invents bright cross/star catchlights.
2. Agents often also pass `Eyes_for_Illustrious…` via `resolve_character_loras(..., include_eye_lora=True)` + trigger `perfect eyes`.
3. Known prior fix pack: `scripts/nsfw/_wildfern_forge_deflare_eyes.py` (eyes-only ADetailer + anti-flare ad prompt/neg).

**Agent rules going forward:**
- Forge refine for keepers: either `adetailer=false`, or eyes-only + **deflare** ad prompt/neg (copy from `_wildfern_forge_deflare_eyes.py`).
- Default ad negative must include: `lens flare, eye flare, star pupils, starburst, glowing eyes, bright catchlights, sparkle eyes`.
- Prefer `include_eye_lora=false` or Eyes weight ≤0.5 when flares show; never stack GlowEyes.
- Soft baseline lighting (liked pack) = no S1, no LensFlare, no Forge face re-detail with empty ad prompts.

---

## Agent checklist (stills)

1. Pick lane: bare `waijfu` for gold finish; `waijfu_house` only when PIP/window invent is the main pain **and** finish still looks good.  
2. Kill invent-light with short tags + negatives — not essay lighting.  
3. Dim: on **Comfy** use Darkness slider (positive); on **Invoke** use dim prompt tags — slider does not work there.  
4. Cast ID **fights lighting** — lower weight or omit when dim/baseline lighting is the goal.  
5. `casting_couch_IL` = empty room only; do not stack on character keepers (hand/foot deform).  
6. Locked BG → mask fill / composite; do not full-frame high-denoise the plate.  
7. If output looks Reed-generic → drop house v4, retry bare waijfu + runtime stack.  
8. **Forge:** never refine keepers with default ADetailer + empty ad prompt — use deflare eyes pack or `adetailer=false`; separate hands/feet passes when room/ID mush digits.  
9. Do not blame owner Invoke lighting LoRAs for agent Forge eye flares.

---

## Fixed-seed lighting baseline pack

**Script:** `D:\studio-agent\temp\_run_lighting_baseline_pack.py`  
**Review folder:** `D:\ComfyBox Images and Videos\Images\Theater Jobs\lighting_baseline\`

| Arm | Folder | Stack |
|---|---|---|
| A | `A_waijfu/` | bare `waijfu` — gold finish bar |
| B | `B_house_v4/` | `waijfu_house` (catalog → v4) |
| C | `C_waijfu_runtime/` | `waijfu` + `Darkness_sliderFin3`@0.7 + `anti_sprawl_IL`@0.55 |

| Test | Seed | Beat |
|---|---|---|
| `L01_closed_night` | 44001 | Closed night room, dim / single practical |
| `L02_pip_bait` | 44002 | Casting couch sit — window/PIP invent bait |
| `L03_saloon_dim` | 44003 | Kneel on wood floor, dim wood walls |
| `L04_face_finish` | 44004 | Portrait close-up — finish / generic-paint check |

**Judge (human):** invent-window/lamp count; overbright; S1 halo; face paint gold vs Reed-generic. Prefer A or C when B loses finish.
