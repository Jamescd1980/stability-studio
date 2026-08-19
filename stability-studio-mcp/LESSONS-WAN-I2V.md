# Lessons learned — Wan I2V (14B / NSFW)

Updated **2026-08-13** — Casting Couch Act 2 **004** double-dildo: Wan I2V needs a **mechanical explanation**, not an SDXL-short prompt. Prior: **2026-08-12** Casting Couch BJ autopsy (004 deepthroat twist fail) + BJ recipe review; catalog `oral_deepthroat` / Ultimate DeepThroat. Prior: **2026-08-11** Casting Couch Darkness **001 lick** keeper (house-best oral lick). Prior: **2026-08-05** generation host CUDA; **2026-08-04** Saloon SS04_002 drip I2V frozen×3; **2026-07-31** Wild Fern dual-face / fake EBSynth; **2026-07-25** SS04 cum; **2026-07-23** SS02; **2026-07-20** Stage2 tease.

## Blame split (so we fix the right layer)

| Layer | Share | What went wrong | Fix |
|-------|------:|-----------------|-----|
| **Tools / defaults** | ~40% | MoE `default` preset used **Lightning 12-step** for keepers; amp defaults high; runner batched beats; lastframe extract flaky | Default preset = **quality (20 step, no Lightning)**; `draft=True` / `moe_preset=fast` only for probes; one-beat runners; solid lastframe extract |
| **Process** | ~35% | Treated each gen as shippable; chained without mid-clip gates; asked for too much motion per chunk; **identity essays** (STYLE/EYE/MOUTH) *or* **SDXL-short motion** (one tag, no mechanics) | One beat / clip; human approve lastframe before chain; gate f0 + mid + last; **explain the motion** (object + where + cycle); never identity essays |
| **Us (agent)** | ~25% | Repeated amp/prompt knobs instead of preset; queued Stage3 mid-Stage2; batched build+slam; overLOCK (eyes/mouth invent faces) | Follow `.cursor/rules/wan-i2v-chaining.mdc`; diagnose frames before retry; stop side-scenes mid-chain |

Not “Wan can’t do video.” Wrong **default quality path** + **process that re-amplified drift**.

## Hard rules

1. **`workflow_id=i2v` = Wan 2.2 I2V-A14B MoE HIGH+LOW** (`studio.wan22_i2v_moe`). Not Wan 2.1 single-UNET, not 5B.
2. **Keepers = quality preset (no Lightning).** Draft/smoke only: `draft=True` or `moe_preset="fast"`.
3. **One Comfy job at a time.** One beat per script run — never comma-batch.
4. **Gate before declaring good:** first frame ≈ start; spot-check ~1s / mid; lastframe usable for chain.
5. **Never prompt female `cum`.**
6. **Free VRAM** after heavy runs when needed.
7. **Delivery layout:** `Video\Theater Jobs\<Scene>\Work\` (WIP) → `Completed Scene\` (finals). Images under `Images\Theater Jobs\<Scene>\Stills\`. See `docs/MEDIA_DELIVERY_LAYOUT.md`. Fails → Recycle Bin.
8. **Rear-view / head-away clips:** do not prompt eyes/mouth (invents a face).
9. **Mouth (front-facing):** drop mouth tags unless the beat is oral. Soft still expression is enough. `mouth opens in pleasure` on high-angle front I2V **melts/deforms the mouth** (CCA2-004 v12). No talk / lip-sync.
10. **Dual-hand beats:** both hands keep moving or one freezes.
11. **Wan motion prompts are explanations, not checkpoint tags.** SDXL stills can live on a short vulgar line. I2V/FLF keepers need: **what must persist** (lead the prompt — toys/shafts vanish if mentioned last) → **where it is in frame** → **the motion cycle (out-and-back)** → act tags → secondary jiggle/face. One-verb still-style lines freeze or move the wrong body. Identity still comes from the start image — do **not** essay STYLE/EYE/MOUTH. Never `detailed face` / `symmetrical eyes` / `camera`.

## Chaining for length (required approach)

Wan single jobs are ~3–4s (49–65f @ 16fps) for identity-critical NSFW. **Longer sequences = approved chain + concat.**

```
still_0  →  clip_A (quality)  →  [gate]  →  last_A
last_A   →  clip_B (quality, one new verb)  →  [gate]  →  last_B
…        →  concat A+B+… = long scene
```

**Per link**

- Length: default **49f** (~3s) for soft/dialogue motion. **Hard contact / dual-face doggy:** prefer **21f (~1.3s) single micro-thrust** then splice/ping-pong — multi-thrust 49f melts eyes first.
- **Short FLF loops (preferred for sex keepers):** `workflow_id=flf2v`, **same forge still** as `image_path` + `end_image_path`, `moe_preset=quality`, action LoRA pair. Prompt must say **out-and-back / return to start pose** (same-still FLF freezes on soft “subtle” verbs). Prefer **`num_frames=21–33`** (~1.3–2s); **13–17f + subtle bob = dead plate** (Saloon BJ02 2026-08-02). Loop/ping-pong in post for longer.
- Res (generation host ~32GB): keepers up to **1080²** / longer clips (65–81f) after smoke; older 20GB notes used **960²**. Do not ship 720×400 when faces matter.
- Prompt: **mechanical explanation of the beat**, not a ComfyUI checkpoint one-liner. Image carries identity (no STYLE/EYE/MOUTH essays). One **beat** per clip — not exit + re-entry + head throw. Never append `detailed face` / `symmetrical eyes` on video (engine video anatomy hint must omit eyes). Same-still FLF: say **out-and-back / backward and forwards**; “slightly” freezes.
- `motion_amplitude` ≤ 0.75 unless user accepts melt risk (PainterI2V-only; no-op on MoE).
- Start: forge still for openers; **only human-approved** lastframe for continuations.
- Fail: recycle that link; retry same link; **never chain a fail**.

**Hard motion** (big lift, slam, insertion): smaller verb, quality preset, consider action LoRA **pairs** (HIGH+LOW) — not longer negatives.

## Presets (`studio.wan22_i2v_moe`)

| preset | Lightning | steps / switch | Use |
|--------|-----------|----------------|-----|
| `default` / `quality` | no | **28** / 14, CFG 3.5, CRF 14 | **Keepers + chain links** |
| `fast` | yes | 8 / 4 | Draft / motion smoke only |

Engine: `generate_video(..., draft=True)` or `moe_preset="fast"` for Lightning; otherwise quality.

### Knobs agents confuse (MoE vs 5B)

| Knob | MoE `workflow_id=i2v` | 5B / Painter |
|------|----------------------|--------------|
| **`motion_amplitude`** | **No-op** (PainterI2V-only). Contact intensity = still + verb + action LoRA + chunk length. | Real — lower = subtler gait |
| **`smooth_motion=true`** | Forces **quality** (no Lightning). Also may inject bundle **`smooth_character`** = `face_naturalizer` + `camera_steady` — **not** a motion smoother | Turns on Painter + gentler amp/fps |
| **`face_lock` bundle** | Just `face_naturalizer`. Helps eyes; over-prompting “face nearly still” can kill drip/moan micro-motion | Same LoRA on single UNET |
| **Keepers** | `moe_preset=quality` / omit + `draft=false` | Prefer MoE for identity NSFW |

## Proven stack

```
HIGH UNET  (+ optional action HIGH)  → KSamplerAdv 0..switch
LOW UNET   (+ optional action LOW)   → KSamplerAdv switch..end
WanImageToVideo; wan_2.1_vae; umt5_xxl
```

- Lightning HIGH+LOW only on `fast`.
- At most **one** action LoRA pair on keepers (+ optional face tools later).
- Orgasm: always HIGH **and** LOW pair.

## Ops checklist

1. `check_gpu_backend` → ComfyUI
2. `check_wan_assets(workflow_id="i2v")`
3. `generate_video(mode=i2v, workflow_id=i2v, …)` — **one** job, quality unless draft
4. Gate f0 / mid / last vs start
5. User approve → extract lastframe → next link
6. Concat approved mp4s for length. Polish: **clean native frames first** (trim / EBSynth / SeedVR @16fps), **RIFE last**. Do not RIFE→SeedVR2 on melted eyes — invents more mush (Saloon lesson).

## Catalog map

| id | Meaning |
|----|---------|
| `i2v` | Wan 2.2 MoE (correct 14B path) |
| `i2v_wan21_native` | Legacy single-UNET Wan 2.1 |
| `i2v_5b` / `*_painter` | 5B draft / Painter motion |

---

## Casting Couch Act 2 — 004 double-dildo (2026-08-13)

**Still:** `User Import\Movie Sex Sceens\Casting Couch Scene\CC act 2\CCA2-004.png` — Frieren on top, V-legs, facing viewer; Darkness torso/breasts cropped at the **bottom of the frame**; thick pink double-ended dildo already in both. Do **not** FLF to 005 (different pose).

**Owner (2026-08-13):** Wan I2V needs **explanations**, not short ComfyUI-checkpoint prompts. v11 (user prompt) was the first clip that “did it.”

### Prompt pattern that worked

Lead with the object that must persist, then where, then the cycle, then act tags, then secondary jiggle/face:

```
thick pink double-ended dildo stays in both pussies, hips at bottom of screen moves backward and forwards, sex, vaginal sex, missionary, mouth opens in pleasure, breast jiggle, butt jiggles
```

Strengthen that same stack with mechanics (persist / vanish / pull-back-then-push-in / with each thrust) — do **not** rewrite it into a one-verb still line.

### Stack (keeper direction)

- Same-still **FLF2V**: `image_path` + `end_image_path` both = `CCA2-004.png`
- `workflow_id=flf2v`, `moe_preset=quality`, `num_frames=33`, `frame_rate=16`
- `lora_bundle=missionary_sex` HIGH+LOW **0.75**
- No `face_naturalizer`, no inpaint end-keys, no free txt2img of a new 004

### Fail log (do not repeat)

| Try | Recipe | Result |
|-----|--------|--------|
| v1 | I2V 21f, missionary 0.65 + face_nat, “thrust hips together” | Frieren **legs** only |
| v2 | Drop missionary, “girl on the bottom thrusts hips” | **Big eyes**, legs |
| v3–v5 | FLF to **warped/inpainted** end keys | Stomach / **stretch-morph**. Owner: inpaint end-keys turn to shit |
| v6 | I2V “hips at the bottom pull back” | Frieren mid-body; Darkness hips still |
| v7 | “torso at the bottom slides down” | Bottom moved; **dildo disappeared** (“slides down” = exit) |
| v8 | More negs, dildo mentioned last | Worse — Wan **weights the start of the prompt** |
| Path A stills | Fresh `waijfu` txt2img | **Wrong room, wrong pose.** Recycled |
| v9 | Same-still FLF, short “slightly bounces”, no LoRA | **Zero movement** |
| v10 | Same-still FLF 33f, missionary 0.75, “bounces hips hard out and back” | Modest mid motion |
| **v11** | User’s explanation prompt + v10 stack | **Keeper direction** (mid MAE ~6.12) |
| v12 | Same stack + strengthened mechanics + `Her mouth opens in pleasure` | **Massive deformed mouth.** Recycled. Drop all mouth prompts on this still |
| v13 | v12 mechanics, **no mouth line**; neg `deformed mouth, gaping mouth, extra mouth` | **FAIL** (owner). Recycled. |
| **v14** | Owner prompt (no jiggle/mouth; neg `moving legs`) + v10 stack | **KEEP.** Ping-pong + drop 1-frame join freeze + **1.25×** → `cca2_004_dildo_v1.mp4` |

**v12 prompt (strengthened from v11):**

```
The thick pink double-ended dildo stays in both pussies the whole time; it does not slip out, vanish, or get replaced. The hips at the bottom of the screen move backward and then forwards in a repeating sex rhythm, pulling back then pushing in, never leaving the bottom of the frame. Sex, vaginal sex, missionary. Her mouth opens in pleasure. Her breasts jiggle with each thrust. Her butt jiggles with each thrust.
```

**Crop fact:** Darkness’s hip joints are **off the bottom of the frame**. Short “hips” maps to Frieren’s V-pelvis. Name **hips at the bottom of the screen** + full sex tags.

**Do not:** inpaint/warp end keys; free txt2img a new 004; FLF to 005; `face_naturalizer`; penis LoRA on a dildo still; Lightning; prompt `camera`; prompt female `cum`; one-verb “slightly” on same-still FLF; prompt **mouth** / `mouth opens in pleasure` on this high-angle front still (v12 deformed mouth).

---

## Saloon SS / vaginal penetration (2026-07-22/23)

Same learning curve as the BJ reel: **action LoRA pair matters**, tip/contact stills fight motion, amp/verb discipline, never full-exit, quality MoE, diagnose frames before retry.

### User gate (authoritative)

| Clip | Path | Status |
|------|------|--------|
| **SS01** | `<DELIVERY>\Video\Frieren\Saloon\SS01.mp4` | **GOOD** (overnight): first **~2s** usable. Full overnight archived as `SS01_overnight_full.mp4`. **Ping-pong the 2s trim** → keeper loop. |
| **SS02** | `…\Saloon\SS02.mp4` | **FAIL** (overnight Missionary Sex): reverted to **side-to-side** motion. |
| **SS03** | `…\Saloon\SS03.mp4` | **FAIL** (overnight Doggy Sex): only **slight hip move** — not real thrust. |
| **SS04_Cum** | `…\Saloon\SS04_Cum.mp4` | Keep (old painted overflow). New jack-o pour: see **SS04 cum recipe** below. |

**Overnight 2026-07-23 gate (user):** SS01 good / SS02+SS03 fail. Next: ship SS01 ping-pong; SS02/SS03 need still+recipe rethink (already-in paint / stronger axial verb / amp), not blind same-stack retry.

**SS02 afternoon experiments (2026-07-23, user gate):** `SS02_expA_insertion.mp4` + `SS02_expB_missionary.mp4` — **both complete FAIL.** f0 locks to `SS02.png` (identity/composition OK); motion never reaches keeper thrust.

| Exp | Stack | Actual failure (pixels) |
|-----|-------|-------------------------|
| **A** | Insertion HIGH 0.35 / LOW 1.0, Cook prompt, amp 0.40 | Lateral body/leg sway; **genital fusion ~1.0s**; ends tip-at-entrance — zero axial in-out |
| **B** | Missionary Sex 1.0/1.0, playtime prompt, amp 0.45 | Mid **wrong anatomy** (floating tip / disconnected shaft) — **not** usable bury; reverts shallow by last |

**Agent misread corrected:** Do **not** treat Exp B ~1.5s as “partial mid bury” or trimmable thrust. It is **genital melt/hallucination**, same discard class as slide-out. Split Insertion weights did not fix the tip-still trap.

**Durable lesson:** When mid looks “deeper,” gate **shaft continuity + labia boundary + axial path** — not gloss/fluid on a melted contact zone. **Change the still first** (SS01 deepest frame / Forge already-in paint); do not iterate LoRA+prompt on `SS02.png` tip contact.

### Technical findings (SS01 probes)

| Attempt | Result |
|---------|--------|
| Tip-at-entrance still + **Missionary Sex** HIGH+LOW | Motion dumped into hands/body **or** full slide-out + vagina melt |
| Tip-at-entrance still + **POV Missionary Insertion** HIGH+LOW @ ~0.6 + stay-buried prompt | Fixed empty vagina / slide-out; **depth stayed shallow** |
| BJ succeeded earlier with **oral insertion** HIGH+LOW | SS initially had **no** action LoRA — same class of miss |

Hard rules confirmed for contact:

- Never prompt **full penis exit**; partial withdraw only for thrusting beats.
- Negate: melt / empty vagina / disappearing shaft / deflating penis.
- **One motion verb** per clip; quality MoE (no Lightning) for keepers; **low amp** on contact (SS01 used ~0.30).
- Diagnose break frames before regenerating the same recipe.

### Insert LoRA vs Sex LoRA (when to use which)

| Beat type | Start still | Prefer LoRA pair | Prompt shape |
|-----------|-------------|------------------|--------------|
| **Insert / tip→in** | Tip at entrance, or tip just outside | **POV Missionary Insertion** (HIGH+LOW) | One verb: push in **and stay buried** — no in-out cycle |
| **Thrust / already-in** | Cock already painted inside | **Missionary Sex** (HIGH+LOW) | Short front-to-back thrusts, **partial withdraw only** |
| **Doggy** | Rear insert / pump | **Doggy Style Sex** I2V HIGH+LOW — `wan2.2-i2v-high/low-doggy-style-sex-14b.safetensors`; Missionary Sex is wrong pose family (causes hip-shake + shaft pulse) | Trigger: *they are having doggy style sex* + front-to-back hip thrusts; stay-inside / partial withdraw |
| **Oral lick** (tongue on tip, **not** tip-in) | Tongue on glans, tip outside / just touching | **Oral insertion** HIGH+LOW @ **0.40** (not 0.6) | One verb: tongue lick along tip — **no** head-slide / deepthroat |
| **Oral bob / tip-in** | Tip-in-mouth, **hands on shaft** | **Oral insertion** HIGH+LOW @ **0.40–0.50** | Mouth / lips slide down then up; **never** prompt `her head` (detaches skull). Neg twisting. Short 13–21f → RIFE half-speed + ping-pong |
| **Oral deepthroat / bury** | Already deep, looking up | **`oral_deepthroat`** = Oral insertion + **Ultimate DeepThroat K3NK** HIGH+LOW (Elven Appetite / Pale Elf Rider proven) | One vertical bury/bob verb; still must allow axial travel (hands on shaft preferred) |

Stack limit (MoE keepers): **Lightning pair (draft only) + at most one action pair**. **Exception — BJ deepthroat:** `lora_bundle=oral_deepthroat` stacks oral_insertion + Ultimate DeepThroat (historical keepers also added K3NK NSFW helper @ ~0.50 via `loras=`). Do not pile Missionary Sex + Insertion + PENIS together.

**MCP (2026-07-26 / 2026-08-12):** `generate_video` accepts catalog **action pairs** + pass-through:
- Bundles: `oral_insertion`, `oral_deepthroat`, `ultimate_deepthroat`, `missionary_sex`, `pov_insertion`, `doggy_sex`, `facial_cum` (+ older orgasm/lightning/nsfw)
- `lora_weights={"pov_insertion_i2v_high": 0.35, "pov_insertion_i2v_low": 1.0}`
- `loras=[{file, weight, branch}]` (or `{id, weight, branch}`) — same as `GenerationEngine`
- `moe_preset="quality"|"fast"`, `draft=True` for Lightning probes

**MCP LoRA checklist (2026-08-01) — before every NSFW Wan I2V keeper:**
1. `resolve_wan_action_loras(prompt=…, beat_hint=…)` → recommended `lora_bundle`
2. If `ready=false` → `download_wan_video_loras(bundle=…)`
3. `generate_video(..., lora_bundle=<id>, moe_preset=quality)`
4. Skipping LoRAs when a bundle matches returns `lora_preflight_warning` (prompt-only bob/insert often fails — Saloon BJ head-still / no-bob lesson)

### Comfybox inventory (action pairs — cataloged)

Under `<MODELS_MOUNT>/StabilityMatrix-win-x64/Data/Models/Lora` (same SM Lora tree):

| Catalog ids | Files |
|-------------|--------|
| `oral_insertion_i2v_{high,low}` | `wan2.2-i2v-high/low-oral-insertion-v1.0.safetensors` |
| `ultimate_deepthroat_i2v_{high,low}` | `wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk` / `…-I2V-101epoc-low-k3nk` |
| `oral_deepthroat` (bundle) | oral_insertion + ultimate_deepthroat (both pairs) |
| `missionary_sex_i2v_{high,low}` | `wan2.2-i2v-high/low-missionary-sex-14b.safetensors` |
| `pov_insertion_i2v_{high,low}` | `wan2.2-i2v-high/low-pov-missionary-insertion-v1.safetensors` |
| `doggy_sex_i2v_{high,low}` | `wan2.2-i2v-high/low-doggy-style-sex-14b.safetensors` |
| `facial_cum_i2v_{high,low}` | `CloseUpFacialCum-v10_{High,Low}.safetensors` (local-only) |

**FacialCum trigger (Elven Appetite keepers — required):** use creator phrasing with **`penis`**, not soft cock-only essays:
`Facial, cum shot, sticky cum, … cum shoots out of the penis and lands on her face`
(+ `cum on face / tongue / chin`, `multiple thick slimy cum shots`). Tip-in stills need **pull tip out then shoot** (EA: light oral ~0.25 + FacialCum ~0.75–0.85 + optional k3nk helper / face_naturalizer). Weight-only bumps without triggers = no ropes.
| `general_nsfw` / `penis_lock` | `NSFW-22-H/L-e8`, `PENISLORA_wan22_i2v_{high,low}` |

On disk but **pass-through only** (not a named bundle): `wan22-k3nk4llinon3-{16epoc-full-high,15epoc-full-low}-k3nk.safetensors` — historical BJ helper @ ~0.50 HIGH/LOW.

Optional alt: `wan2.2_i2v_{high,low}noise_pov_missionary_v1.0.safetensors` (dtwr434) — not cataloged; pass via `loras=[{file,weight,branch}]`.

### Recipe templates (I2V motion-only)

**Insert beat (tip→bury, one shot):**
```
nsfw, he slowly pushes his cock into her pussy and stays buried,
vaginal penetration, cock remains inside, steady view
```
Neg: `full withdrawal, penis slides out, empty vagina, melting pussy, deflating penis, disappearing shaft, …`  
LoRA: Insertion @ ~0.55–0.65 · amp ≤ 0.35 · 49f · quality

**Thrust beat (already-in):**
```
nsfw, short front-to-back thrusts with his cock staying inside her pussy,
partial withdraw only, vaginal penetration, steady view
```
Neg: same exit/melt block · LoRA: Missionary Sex @ ~0.5–0.6 · amp ≤ 0.40 · 49f · quality

Say **view / POV**, not **camera** (house still rule — camera spawns props; Saloon BJ prompts still say “steady camera” and should be cleaned to “steady view”).

### Casting Couch oral lick (house-best, 2026-08-11)

User call: **best lick scene we have ever made.** Do not “improve” by raising LoRA weight or swapping to Hunyuan.

| Field | Value |
|-------|--------|
| **Still** | `Images\Theater Jobs\Casting Couch\review\darkness_cc_sex001_lick_v3.png` (Fixed → Forge 0.20, AD off) |
| **Clip** | `Video\Theater Jobs\Casting Couch\Work\darkness_cc_sex001_lick_v1.mp4` → promote to `Completed Scene\` when packing |
| **Engine** | Wan 2.2 MoE **14B** `workflow_id=i2v` — **not** 5B, **not** Hunyuan (assets missing + `generate_video` routing TBD) |
| **Preset** | `moe_preset=quality`, `draft=false`, 28-step / no Lightning |
| **Size / length** | **1024²**, **49f @ 16fps** (~3.06s) |
| **LoRA** | `lora_bundle=oral_insertion` @ **0.40 HIGH + 0.40 LOW** (default 0.6 pushes tip-in / swallow) |
| **Pos** | `her tongue slowly licks along the tip of his cock` |
| **Neg** | `full penis exit, empty mouth, tip vanishing, deflating shaft, disappearing shaft, melting, morphing face, camera, dslr, deepthroat, head sliding down` |
| **Gate** | f0≈still **0.9998**; mid moves **~0.79**; last still lick beat **~0.90** (mild tip-in LoRA pull OK) |

**Do not:** essay the still into the prompt; use oral_insertion @ 0.6 on a tongue-only still; Hunyuan until wired; Lightning/draft for keepers.

### Casting Couch BJ bob (003 keeper + length post, 2026-08-12)

| Field | Value |
|-------|--------|
| **Still** | `darkness_cc_sex003_inmouth_v3.png` — tip-in, **both hands gripping shaft** |
| **Raw** | `darkness_cc_sex003_bob_v2.mp4` — 13f / oral_insertion @ **0.40** / `she takes his cock deeper, lips stay wrapped around the shaft` |
| **Usable** | `darkness_cc_sex003_bob_v3.mp4` — RIFE→half-speed @16fps → ping-pong (~3.25s). Promote: `Completed Scene\` |
| **Fail that taught** | Prompt `her head slides down…` → **skull detach + shaft vanish**. Never say **her head** on oral I2V. |

### Casting Couch 004 deepthroat autopsy (2026-08-12) — why Elven Appetite / Pale Elf Rider worked and we failed

**User ask:** we already shipped vertical BJ deepthroat/bob on Elven Appetite + Pale Elf Rider / Saloon. Why is Casting Couch 004 only twisting?

**Blame split (not “Wan is broken”):**

| Lever | Elven Appetite / Pale Elf Rider keepers | Casting Couch 004 tries (v1–v4) |
|-------|------------------------------------------|----------------------------------|
| **Action LoRA** | **`oral_insertion` + `Ultimate DeepThroat K3NK`** (and often K3NK NSFW helper) — see `scripts/nsfw/run_bj_wan22_loras.py` @ oral 0.75 + DT 0.45 + helper 0.50 | **`oral_insertion` alone** @ 0.40–0.55. Ultimate DeepThroat was **on disk but not in MCP catalog** until 2026-08-12 — agents could not `lora_bundle` it |
| **Still pose** | POV oral with room for axial travel (hands free or on shaft / crop allows up-down) | **`004_deepthroat` = arms behind back**, looking straight up the shaft — neck locked; Wan spends motion budget on **yaw/twist** |
| **Contrast still** | — | **`003_inmouth` hands-on-shaft** → bob keeper with oral_insertion alone. Pose > prompt |
| **Prompt** | Historical: `head moves/goes down the shaft… rhythmic bobbing downward` (risky wording but DT LoRA carried vertical) | Soft “deeper into throat” / “mouth slides down” without DT LoRA → twist or melt; `her head…` → detach |
| **Same-still FLF** | Saloon BJ01 FLF bob worked with **out-and-back** language + action stack | Same-still FLF on 004 with soft verb → **frozen plate** (dmse≈0) |

**Hard rules (BJ recipe — review):**

1. **Still gate before gen:** hands **on shaft** (or free) for vertical bob/deepthroat. **Arms behind back / neck locked looking up the pole** → do not expect axial bob; keep as still or re-pose / use 003-class still.
2. **Deepthroat / deep bury LoRA:** use `lora_bundle=oral_deepthroat` (oral_insertion + Ultimate DeepThroat). Tip-suck / soft bob can stay `oral_insertion` @ 0.40. Lick = oral @ 0.40 and **negate** deepthroat.
3. **Never prompt `her head`** on oral I2V (detach). Prefer `her mouth` / `she takes his cock deeper` / `lips stay wrapped`.
4. **Neg for bob:** `twisting, turning, rotating, tilting, looking aside, pulling off, empty mouth, biting, severed, detached head, disappearing penis…`
5. **Length:** short 13–21f keeper → RIFE in-betweens → play half-speed @16fps → `splice_pingpong` (down then reverse-up). Do not ask one Wan run for a long bob cycle on hard contact.
6. **Catalog gap fixed 2026-08-12:** Ultimate DeepThroat + `oral_deepthroat` bundle added to `studio/wan_video_loras.py`. Restart MCP to pick up. Optional K3NK helper still via `loras=[{file,weight,branch}]`.

**Log:** `Video\Theater Jobs\Casting Couch\Work\logs\cc_bj_004_deepthroat_autopsy_2026-08-12.md`

### Workflow levers (ranked for Saloon next)

1. **Post: SS01 first-2s ping-pong** — production win without new gens (`splice_pingpong` / `splice_pose_matched_loop`).
2. **Still prep: paint cock already deep** → I2V thrust with Sex LoRA (tip stills resist tip→deep bury).
3. **Pose-correct action LoRA** — Doggy pair for SS03; don’t reuse Missionary Sex on doggy stills.
4. **Chain from best midframe** — extract approved mid where penetration looks best; next chunk = stay-buried micro-thrust only.
5. **PENISLORA light** (~0.4–0.55) if shaft melts while contact holds.
6. **Deep-stroke / contact length** — two paths:
   - **LF→I2V chain (Saloon proven):** gate deepest clean frame → optional Forge → next quality MoE chunk one verb → concat/ping-pong. Still the default for Saloon deep-stroke sequences.
   - **MoE FLF2V (Wild Fern ship probe):** `studio/wan22_flf2v_moe.py` + scripts under `scripts/nsfw/_prep_flf_*` — first+last keys, quality MoE, **short length (21f)**. Also MCP `workflow_id=flf2v` + `image_path` + `end_image_path`. Do not ask FLF for multi-thrust 49f on dual-face doggy.
7. **PainterI2V** — 5B motion amp tool only; **not** for face/body lock or identity-critical NSFW contact. Stay on `workflow_id=i2v` MoE.
8. OpenPose/ControlNet hip thrust — optional later; still+LoRA+verb usually wins first.

### SS04 cum recipe (jack-o pour → face, 2026-07-24/25)

Still lineage: `SS04-1.png` → honey bias → Forge `SS04-1_opaque.png` → **T13 keeper base**. Output: `Video\Frieren\Saloon\`. Full T2–T13 log: `outputs/saloon_SS04_cum_look_vs_bj.md`.

| Try | Stack | Gate |
|-----|-------|------|
| T1 | `female_orgasm` 0.75 + pour/pulse + long neg | **Pee/squirt** — recycled |
| T2 | no LoRA; opaque white pos; amp 0.42 / 43f; short pee neg | **Motion OK**, fluid soft |
| T3 | face-lock (“face nearly still”) + amp 0.35 | **Static** — recycled |
| T4 | FacialCum HIGH+LOW @**0.70**; eyes closed + massive drip; amp 0.42 / 45f | Opaque coat candidate; aerial/chest bias |
| T7 | FacialCum **LOW only** @0.50; face-coat path; amp 0.42 / 64f | Motion/path loved; fluid not cum-like |
| T8 | dairy stack (milky/creamy/jizz) + FacialCum LOW @0.55 | **Miracle Whip / frosting** |
| T9 | **No FacialCum**; lean `thick white cum` + pussy→face; amp 0.42 / 64f | **Watery steam** — white, no viscosity |
| **T10** | `semen, sticky cum, cumshot` + FacialCum **HIGH+LOW @0.40**; amp **0.40** / 64f | **Best look frozen** — body/penis still; only cum moved |
| T11 | T10 stack + volume/hips language; amp **0.52** / 64f | **Honey + breast aim** (more motion, wrong material/aim) |
| T12 | lean pos + FacialCum @0.35; amp 0.45; raw `SS04-1.png` | Face OK + volume; **honey** (still bias + warm light) |
| **T13** | Forge **opaque still** + lean pos + FacialCum H+L @0.40; amp **0.42** / 64f | **Keeper base** — solid/story match; lots of cum; face OK. Leave in place. |

**Hard rules from this arc**

1. **One beat per clip.** Overflow + face coat + body/penis motion + opacity fix in one job **fails**. Split: still prep → overflow (or tip-out still) → facial shoot.
2. **Honey = still bias + warm saloon light.** Translucent amber contact on `SS04-1.png` grows into honey ropes under volume. Prompt lean alone cannot invent opacity.
3. **Opaque still prep helps f0.** Forge refine on contact fluid → `SS04-1_opaque.png` fixed milky f0 for T13.
4. **Miracle Whip** = milky/creamy/jizz dairy stack (+ FacialCum overcook). **Water** = bare thick-white / no LoRA. Viscosity tokens + paired FacialCum @~0.4 for semen look.
5. **FacialCum HIGH+LOW on correct branches** (HIGH=dynamics, LOW=appearance). Use for **facial shoot** (tip→face), not as the main lever for pussy-overflow pour. Never LOW-only for look. Catalog cannot download it — local `CloseUpFacialCum-v10_{High,Low}.safetensors` on comfybox.
6. **Wan full pull-out melts.** Prefer **tip-out / partial withdraw** still (LF2I penis-only), then I2V **one verb: facial cumshot**. Do not ask one clip for exit + ropes + face.
7. **User (2026-07-25):** T13 solid / story match; script OK for leak **or** pullout; happy with lots of cum + face OK. Next = tipout still → facial I2V (T13b); do not auto-concat until keep.

**T13b facial (ran 2026-07-25):** tipout still `SS04_1_T13_tipout.png` (hard-mask LF2I; soft tip-out) → `SS04_1_v2_T13b_facial.mp4` — FacialCum H+L @0.40, amp 0.42 / 64f quality, lean face pos. Gate: partial face hit (cheek/chin) + chest wet; not BJ rope shoot. Tipout still too shallow. Leave T13+T13b; no concat until user keep.

**Tipout still lesson:** MCP soft mask + ControlNet depth ≈ no pixel change. Use local `engine.inpaint_advanced` + **hard white rect** mask, no depth. Forge full-frame tip-out drifts room/identity.

**Runner:** `py -3 scripts\nsfw\run_ss04_1_cum.py V2_T13` · `V2_T13b`

### SS04_002 drip-into-mouth (2026-08-04) — frozen plate

Still: `SS04_002_forge_soften.png`. Goal: **one verb** — cum strand drip into open mouth. Game beat left **still-only** (sparse Saloon wiring).

| Try | Recipe | Result |
|-----|--------|--------|
| v1 `00178` | FacialCum H+L @**0.40**, 49f quality, drip prompt; `motion_amplitude=0.40` | **Frozen** (mean frame-diff ~0.22). Recycled |
| v2 `00179` | FacialCum @**0.30**, 41f, stronger drip verb + frozen neg | Still frozen (~0.24). Recycled |
| v3 `00180` | **No LoRA**, 41f quality, same drip verb | Still frozen (~0.22). Recycled |

**Blame:** MoE locks hard contact stills; FacialCum does not unlock strand physics. **`motion_amplitude` is PainterI2V-only — ignored on `workflow_id=i2v` MoE.** Prompt/LoRA knobs alone did not create drip motion.

**Next lever (not run — user skipped):** FLF with an end still where the strand has advanced, or accept still-only. Do not keep retrying FacialCum weight / longer negatives.

### Wild Fern strap / dual-face (2026-07-31) — EBSynth autopsy

**Still:** `Movie_WildFern_04_darkness_strap.png` (1920×1080 game CG) → I2V at 960×544. Two faces in frame (Darkness lookback + Fern behind). Contact = strap doggy.

**What failed**

| Clip / test | Result | Why |
|-------------|--------|-----|
| MoE I2V 720×400 | mouth/hips wrong, mush | under-res + eye redraw |
| `studio_agent_wan22_moe_00153` HQ 960×544 quality | hips better; **eyes melt mid** | dual-face contact regenerates faces every frame; 49f multi-thrust too much |
| `FD_00153_ebsynth_test.mp4` | **trash** (user reject) | **Not EBSynth.** `ebsynth.exe` missing → OpenCV **static still-face alpha paste** |

**OpenCV “restore” numbers (00153 vs key `WF04_flf_first`):**

- Mid-clip Darkness face drifts hard from key (raw−key MAD ~19–36 in face box).
- “Restore” glues faces back to the **unwarped key** (rest−key face ~4.5) while body keeps thrusting (rest−raw face ~17–34, hips barely touched ~3–4).
- Diff map: strong face/hair edges = frozen plate over moving heads → ghosting / detached eyes. Dual-face mask hits **both** faces.

**Hard rules from this arc**

1. **OpenCV face-lock ≠ EBSynth.** PatchMatch warp vs alpha-blend of a static still. Never ship OpenCV fallback as “EBSynth test.” Fail loud if `tools/ebsynth/ebsynth.exe` is missing (`--allow-opencv-fallback` only for throwaway probes).
2. **Cannot polish melted dual-face mid-clip** by pasting f0 faces. Fix gen: shorter clip, FLF keys, quality MoE, or real temporal restore.
3. **Hard contact keepers:** ~**21f / one micro-thrust**; splice/loop for length. Prefer quality ≫ seconds.
4. **Parallel pipeline idea stays valid** (ComfyBox gens next link while main rig restores prior) — but restore step requires **real EBSynth binary** (jamriska win64 → `tools/ebsynth/ebsynth.exe`). PyPI `ebsynth` package is a stub; jamriska.cz DNS was down at test time.
5. **MCP gaps (do next):** wire `workflow_id=flf2v` into `generate_video` (builder exists, engine still I2V-only); never auto-label OpenCV as EBSynth; restart MCP process after `hardware_profile` / video anatomy hint changes so agents get 960² + no `symmetrical eyes` on video.

### What NOT to repeat

- Missionary **Sex** LoRA on tip-at-entrance stills expecting a clean bury.
- Full in-out / “slides out” language on insert beats.
- Lightning / draft for contact keepers.
- Amp > ~0.4 hoping for deeper penetration.
- Stacking multiple NSFW action pairs.
- Chaining a failed SS03 / melt tail.
- PainterI2V / `i2v_5b` for Saloon SS keepers.
- Blind retry without viewing the break frames.
- Calling genital **melt** “partial bury” because mid looks busier — verify shaft continuity before any trim/ping-pong hope.
- SS02 tip still + any action LoRA without still prep (Insertion split weights included).
- SS04: `female_orgasm` on pour beats (pee); face-lock / “face nearly still” (kills drip); long pee/anatomy neg essays.
- SS04: dairy/milky/creamy essay (Miracle Whip); bare thick-white with no LoRA (water); FacialCum LOW-only; re-I2V from raw honey still without opaque prep; **full pull-out** in I2V; packing overflow+face+motion+opacity into one clip.
- Wild Fern: OpenCV still-face paste sold as EBSynth; 49f multi-thrust dual-face doggy as one keeper; polishing melted eyes; `detailed face` / `symmetrical eyes` on I2V.
