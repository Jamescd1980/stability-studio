# Merge Phase 0 — `waijfu_alpha` × `Reedxxx` baselines

**Status:** Phase 0 only. **No merge.** No darkness bake. No Pony→IL LoRA downloads.

**Date:** 2026-07-26

## Locked decisions (later phases)

| Decision | Status |
|----------|--------|
| **Darkness / dim lighting** | Stays a **LoRA** (slider weight). **Do not bake** into house ckpt. |
| **Facesitting** | **Nice to bake into checkpoint later** (post-merge / fine-tune). Not Phase 0. Include baseline prompt for future A/B. |
| **Fewer LoRAs** | House ckpt should carry character + sex prior so cast LoRAs are optional, not required. |
| **Windows / on-screen light invent** | Shared vice of both parents — merge will not fix; handle with LoRA + prompt later. |

## Checkpoints located

### A — `waijfu_alpha` (primary generation host = ComfyBox)

| Field | Value |
|-------|--------|
| **Canonical (usable)** | `/mnt/game/StabilityMatrix-win-x64/Data/Models/StableDiffusion/waijfu_alpha.safetensors` (ComfyBox) |
| **Size** | 7,105,347,638 bytes (~6.62 GiB) |
| **Arch** | SDXL / Illustrious-family (dual text encoders; `conditioner.embedders.*` + UNet) |
| **Windows SM stub** | `D:\StabilityMatrix-win-x64\Data\Models\StableDiffusion\waijfu_alpha.safetensors` — **0 bytes** (Recuva stub; do not use for merge until restored from ComfyBox) |

### B — `Reedxxx` / `reedXXXIllustrious`

| Field | Value |
|-------|--------|
| **Canonical usable** | `D:\Invoke AI\models\5ca8a54f-3b4d-4cb3-b685-60817f99a3d7\reedXXXIllustrious_v150.safetensors` |
| **Hardlinked house paths** | `D:\Extra Models\Reedxxx\reedXXXIllustrious_v150.safetensors` · `D:\StabilityMatrix-win-x64\Data\Models\StableDiffusion\reedXXXIllustrious_v150.safetensors` |
| **ComfyBox (for MCP gens)** | `/mnt/game/StabilityMatrix-win-x64/Data/Models/StableDiffusion/reedXXXIllustrious_v150.safetensors` |
| **Size** | 7,105,355,864 bytes (~6.62 GiB) |
| **Arch** | SDXL (`modelspec.architecture = stable-diffusion-xl-v1-base`) / Illustrious-family |
| **Dead stubs** | `D:\Recover_Intake\Extra Models\Reedxxx\reedXXXIllustrious_v140.safetensors` and loose `v140` copies — **0 bytes** |

`D:\Extra Models\` itself was empty; Reedxxx lived under Recover_Intake / Invoke until hardlinked into Extra Models + SM.

**MCP `checkpoint=` filenames:**

- `waijfu_alpha.safetensors`
- `reedXXXIllustrious_v150.safetensors`

## Baseline output folders

```
D:\ComfyBox Images and Videos\Images\merge_phase0_baselines\waijfu\
D:\ComfyBox Images and Videos\Images\merge_phase0_baselines\reedxxx\
```

Matching filenames per test id (e.g. `P01_frieren_nocolora_s42.png`).

## Frozen gen settings

| Knob | Value |
|------|--------|
| `style` | `waijfu` (anime / Illustrious house lane) |
| Character LoRAs | **none** (no cast LoRA stack) |
| Action / darkness LoRAs | **none** for Phase 0 baselines |
| Size | style default (stay within `generation_limits`) |
| Sampler / steps / cfg | style defaults unless noted |
| `content_rating` | `open` |
| `face_detail` | style default |

Shared negative (all tests):

```
lowres, worst quality, bad anatomy, bad hands, extra digits, mutated hands, poorly drawn face,
text, watermark, logo, signature, blurry, jpeg artifacts, camera, dslr, camcorder, lens,
smartphone, selfie stick, window, against glass, glass wall, balcony
```

Yuri / multi-girl extras (P03, P04 only) append:

```
extra people, 1boy, 2boys, man, male, male hand, male arm, disembodied hand, couple, hetero, penis, cock, pov hand
```

---

## Test pack (frozen prompts + seeds)

### P01 — Named character, no cast LoRA (Frieren)

- **Seed:** `42001`
- **Goal:** Does waijfu still know Frieren without LoRA? Does Reedxxx fail identity?
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
bedroom interior, soft ambient light, anime++, bold outline, cel-shaded coloring,
upper body view, solo focus, 1girl, Frieren, long silver hair, green eyes, pointed ears,
elf, naked, flushed cheeks, looking at viewer, sitting on bed
```

### P02 — Clear sex position (doggy / vaginal)

- **Seed:** `42002`
- **Goal:** Contact / pose clarity (expect waijfu stronger).
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
bedroom interior, soft ambient light, anime++, bold outline, cel-shaded coloring,
View from mans POV, solo focus, 1girl, long silver hair, green eyes, pointed ears, elf,
naked, flushed cheeks, look of pleasure on her face, mouth open as she looks back over her shoulder at the man,
on her hands and knees, legs slightly spread, man behind her shoving his cock in her pussy,
man grabs her hips, doggystyle, vaginal penetration
```

### P03 — `2girls, yuri, lesbian`

- **Seed:** `42003`
- **Goal:** Girls-only / lesbian framing (expect Reedxxx a bit better; both may sneak a man).
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
bedroom interior, soft ambient light, anime++, bold outline, cel-shaded coloring,
side view, 2girls, yuri, lesbian, no men,
girl with long silver hair kissing girl with short purple hair,
both naked, fingering her pussy, wet pussy, flushed cheeks
```

### P04 — `3girls` threesome (fff)

- **Seed:** `42004`
- **Goal:** Multi-subject count / layout (expect Reedxxx).
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
bedroom interior, soft ambient light, anime++, bold outline, cel-shaded coloring,
wide shot, 3girls, yuri, lesbian threesome, no men,
three naked girls on a bed kissing and fingering each other,
silver hair, purple hair, blonde hair, wet pussy, flushed cheeks
```

### P05 — Wide / upper-body (anti close-up)

- **Seed:** `42005`
- **Goal:** Framing obedience (expect Reedxxx; waijfu close-up tic).
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
living room interior, soft ambient light, anime++, bold outline, cel-shaded coloring,
wide shot, full body, upper body visible, standing, 1girl, long silver hair, green eyes,
pointed ears, elf, casual dress, looking at viewer, hands at sides
```

### P06 — Indoor solid wall + pictures (window trap)

- **Seed:** `42006`
- **Goal:** Solid picture wall without inventing a window.
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
indoor bedroom, solid wall behind her covered with framed pictures and posters, no window,
soft ambient light, anime++, bold outline, cel-shaded coloring,
upper body view, 1girl, long silver hair, green eyes, pointed ears, elf, naked,
sitting on bed, looking at viewer, flushed cheeks
```

### P07 — Dim interior (no lamp tokens)

- **Seed:** `42007`
- **Goal:** Dim room without lamps / nuke-bright / window light source. (Darkness LoRA later — not in ckpt.)
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
dim lighting, soft lighting, ambient light, dark bedroom interior, solid walls, no window,
anime++, bold outline, cel-shaded coloring,
upper body view, 1girl, long silver hair, green eyes, pointed ears, elf, naked,
sitting on bed, looking at viewer
```

### P08 — Facesitting (optional baseline for later bake compare)

- **Seed:** `42008`
- **Goal:** Record parent behavior now; **facesitting bake = post-merge goal**, not Phase 0.
- **Positive:**

```
masterpiece, best quality, absurdres, newest, very aesthetic, perfect eyes,
bedroom interior, soft ambient light, anime++, bold outline, cel-shaded coloring,
View from mans POV, 1girl, long silver hair, green eyes, pointed ears, elf, naked,
facesitting, sitting on his face, pussy on face, looking down at viewer, flushed cheeks,
thighs around his head
```

---

## Baseline run log

Settings used: `style=waijfu`, no LoRAs, 1024×1024, steps 28, cfg 6, euler_ancestral, `face_detail=false`, seeds as frozen.  
P07/P08 not generated this pass (priority six first).

| ID | Priority | waijfu file | reedxxx file | Winner | Notes |
|----|----------|-------------|--------------|--------|-------|
| P01 | **yes** | `…/waijfu/P01_frieren_nocolora_s42001.png` | `…/reedxxx/P01_…` | **waijfu** | Both know Frieren without LoRA; waijfu more iconic + more body; Reed closer crop + lamp |
| P02 | **yes** | `…/waijfu/P02_doggy_s42002.png` | `…/reedxxx/P02_…` | **Reedxxx** (contact) / **tie fail** (doggy) | Neither did lookback doggy; both drifted cowgirl. Reed clearer penetration/contact |
| P03 | **yes** | `…/waijfu/P03_yuri2_s42003.png` | `…/reedxxx/P03_…` | **waijfu** (seen) | waijfu: clean 2girls kiss/yuri, no man in frame. Reed: file OK; vision caption blocked — glance folder |
| P04 | **yes** | `…/waijfu/P04_3girls_s42004.png` | `…/reedxxx/P04_…` | **glance** | Both generated; NSFW multi-girl vision caption blocked — open pair side-by-side |
| P05 | **yes** | `…/waijfu/P05_wide_s42005.png` | `…/reedxxx/P05_…` | **tie / slight Reed** | Both obeyed full-body wide doorway; Reed dimmer room read; both invent lamps |
| P06 | **yes** | `…/waijfu/P06_picturewall_s42006.png` | `…/reedxxx/P06_…` | **waijfu** (no window) | Both: solid wall + framed pictures, **no window**. Reed adds bedside lamp; waijfu cleaner wall lock |
| P07 | skipped | — | — | — | dim (no lamps) — freeze prompt remains for later |
| P08 | skipped | — | — | — | facesit baseline — freeze prompt remains for later bake compare |

## Verdict table (after viewing)

| Test | waijfu | Reedxxx | Winner |
|------|--------|---------|--------|
| P01 Character no-LoRA | Strong Frieren ID, red earrings, upper body | Also Frieren ID, tighter face crop, lamp | **waijfu** |
| P02 Doggy / sex pose | Face/body good; pose wrong (cowgirl/hover) | Clearer sex contact; also cowgirl not doggy | **Reedxxx** contact; **both miss doggy** |
| P03 2girls lesbian | 2girls yuri kiss, girls-only OK | Needs human glance | **waijfu** (provisional) |
| P04 3girls | Needs human glance | Needs human glance | **TBD — open folder** |
| P05 Wide / anti close-up | Full body doorway — good | Full body doorway + dimmer — good | **tie** (Reed slight mood) |
| P06 Picture wall / no window | Pictures on solid wall, no window | Same + lamp invent | **waijfu** |
| P07 Dim (no lamps) | not run | not run | — |
| P08 Facesitting | not run | not run | — |

### Summary (after grids)

- **Character without LoRA:** both parents can do Frieren; **waijfu** still the keeper for identity finish.
- **Sex contact:** Reedxxx looked more “in” on this seed; **neither obeyed doggystyle lookback** — protect pose blocks in merge, don’t trust WS alone.
- **Wide shot:** surprise — **waijfu did not face-fill** on P05; Reedxxx matched. Close-up tic may be prompt-sensitive.
- **Window trap:** **both passed** on P06 (pictures stayed on solid wall). Lamp invent remains (Reed worse).
- **Multi-girl:** P03 waijfu looks usable; **confirm P03 Reed + both P04 yourself** (vision filter blocked captions).
- **No merge performed.** Darkness stays LoRA. Facesitting bake = later.

## Prompt tag rule (Illustrious sex positions)

For **doggy / rear-entry / strap-on rear** tests, the positive prompt **must include the exact tag `doggystyle`**.  
Do not rely on “doggy”, “from behind”, “ass up”, or pose prose alone — Illustrious parents respond to the Danbooru-style tag.  
(FD01 Fern–Darkness strap-on beat already used `doggystyle`; no regen required.)

---

## Fern–Darkness sex smoke (paired parents)

**Date:** 2026-07-26  
**Status:** Smoke only. **No merge.** No darkness bake. No Wan video.  
**Goal:** Same prompt + seed on `waijfu_alpha` vs `reedXXXIllustrious_v150` with Fern + Darkness lesbian sex beats.

### Inventory (source pack)

| Still | Path | Notes |
|-------|------|--------|
| 001 | `Video/Fern -Darkness/stills/general/001.png` | Invoke metadata = strap-on doggystyle (Nb_Fern / Nb_darkness); = zip `d46ab8aa…` |
| 002–004 | same folder | Canvas-edited; act text stripped from metadata — used as pack context only |
| zip | `Fern and Darkness_….zip` | 5th frame `1f42936b…` not copied into stills |

Beats chosen for smoke (T2I, scene-matched; not i2i): **FD01 strap-on doggystyle**, **FD02 facesit**, **FD03 69**, **FD04 face-lick / cunnilingus**.

### Output folders

```
D:\ComfyBox Images and Videos\Images\merge_phase0_baselines\fern_darkness_smoke\waijfu\
D:\ComfyBox Images and Videos\Images\merge_phase0_baselines\fern_darkness_smoke\reedxxx\
```

### Gen settings (match Phase 0 baselines)

| Knob | Value |
|------|--------|
| `style` | `waijfu` |
| Character LoRAs | **none** (Darkness not in `resolve_character_loras`; Fern LoRA available but skipped) |
| Size / steps / cfg | 1024×1024, 28, 6, `euler_ancestral` |
| `face_detail` | false |
| `content_rating` | open |
| Negatives | Phase 0 shared + yuri male-block |

### Frozen prompts + seeds

#### FD01 — Strap-on doggystyle (ref still 001) — seed `42101`

Tags include **`doggystyle`**. Role in prompt: Darkness behind Fern with thick strap-on dildo.

#### FD02 — Facesitting — seed `42102`

Darkness sitting on Fern's face, pussy on face, cunnilingus / facesitting.

#### FD03 — 69 — seed `42103`

Sixty-nine, licking each other's pussy.

#### FD04 — Face lick / cunnilingus close-up — seed `42104`

Fern between Darkness's legs licking her pussy; close-up side view.

### Run log / winners

| ID | Beat | waijfu | reedxxx | Winner | Issues |
|----|------|--------|---------|--------|--------|
| FD01 | strap-on **doggystyle** | `…/waijfu/FD01_strapon_doggy_s42101.png` | `…/reedxxx/FD01_…` | **tie on pose** / **Reed** env | Both got rear doggy + strap-on harness. **Role swap** vs prompt (Fern giving, Darkness receiving). waijfu: **window invent** + plants. Reed: **lamp invent**, picture on wall, no window. IDs OK no-LoRA. No male hand. |
| FD02 | facesit | `…/waijfu/FD02_facesit_s42102.png` | `…/reedxxx/FD02_…` | **neither** (Reed worse) | waijfu: **missed facesit** → face-lick / close cuddle. Reed: closer to facesit but **male genitalia leak** at contact + Darkness hair short. Plants. |
| FD03 | 69 | `…/waijfu/FD03_69_s42103.png` | `…/reedxxx/FD03_…` | **Reedxxx** | waijfu: intimate missionary / nuzzle — **not 69**; **window + blinds**. Reed: clear **69 / mutual oral**, wood wall, framed picture edge, **no window/lamp**. No male hand either. |
| FD04 | face lick / oral | `…/waijfu/FD04_facelick_s42104.png` | `…/reedxxx/FD04_…` | **Reedxxx** (contact) / **waijfu** (ID framing) | Both cunnilingus. waijfu: medium two-shot + **window** + plant; fingering hand a bit mushy. Reed: tighter oral close-up, wood wall, **no window/lamp**; Darkness mostly cropped to blonde/face edge. No male hand. |

### Axis summary (lesbian smoke)

| Axis | waijfu | Reedxxx |
|------|--------|---------|
| Lesbian contact / act clarity | Softer; drifts to cuddle/kiss on FD02–03 | Stronger oral/69 contact (FD03–04); FD02 futa/cock leak |
| Multi-girl / IDs (no LoRA) | Both readable; Fern purple + Darkness blonde | Same; FD02 Darkness weaker (short hair) |
| Close-up obedience | FD04 medium; can invent window | FD04 tighter crop (good for oral; crops partner) |
| Male-hand / hetero leak | Clean on this pack | **FD02 cock/balls invent** — watch Reed on facesit |
| Windows / lamps | **Window habit** (FD01, FD03, FD04) | **Lamp** on FD01; cleaner walls on FD03–04 |

### Takeaways for blend

- **`doggystyle` tag works** on both parents for strap-on rear (FD01) — keep that tag mandatory for rear tests (see rule above). Role assignment still fragile without LoRAs.
- **Reedxxx** better at complex oral/69 contact; **waijfu** cleaner girls-only (no cock) but weaker pose obedience + window invent.
- No cast LoRAs used; identity held via hair/eye tags. Darkness has **no** house LoRA entry yet.
- **No merge performed.**

## Explicit non-actions this phase

- [x] No ModelMerge / CheckpointSave merge
- [x] No darkness baked into ckpt
- [x] No Pony darkness / facesitting LoRAs downloaded onto Illustrious
- [x] Fern–Darkness smoke: no merge / no Wan / no darkness bake
- [ ] Phase 1 WS merge — **not started**
