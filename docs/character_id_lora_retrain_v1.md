# Character ID LoRA retrain v1 (style / lighting soak fix)

Goal: **identity + composition influence only** — not style/lighting. Style stays on **waijfu**.  
Status:
- **Fern / Frieren / Darkness:** id_v1 July 2026; **rematched 2026-08-10** — same caption bucket as rest (no stamped `soft lighting`). Output: `/mnt/game/lora-training/output/id_v1_match/`.
- **Ubel / Flamme / Cha Hae In / Jinah Sung / Joo Hee:** **done** (2026-08-10) — rest chain trained + installed to ComfyBox SM + `D:\Extra Models\Character LoRA's`. Logs: `/mnt/game/lora-training/output/id_v1_rest_*.log`.

## Datasets (found)

| Char | Count | Source | Trigger (keep) |
|------|------:|--------|----------------|
| Fern | 123 | `D:\Bad boy\Raw Images\GrimoireOfDesires\Fern` (`nbf_fern_*.jpg`) | `nb_fern` |
| Frieren | 108 | `D:\Bad boy\Raw Images\GrimoireOfDesires\Frieren` | `nb_frieren` |
| Darkness | 158 | `D:\Bad boy\Raw Images\Konosuba\Darkness` (`nbk_darkness_*.jpg`) | `nbk_darkness` |
| Ubel | 111 | Grimoire / ComfyBox `datasets/ubel` | `nb_ubel` |
| Flamme | 117 | Grimoire / ComfyBox `datasets/flamme` | `nb_flamme` |
| Cha Hae In | 94 | SoloLeveling / `datasets/cha_hae_in` | `nb_cha_hae_in` |
| Jinah Sung | 70 | SoloLeveling / `datasets/jinah_sung` | `nb_jinah_sung` |
| Joo Hee | 58 | SoloLeveling / `datasets/joo_hee` | `nb_joo_hee` |

Staged (hardlinks + skeleton `.txt`):  
`D:\studio-agent\training\id_lora_v1\{fern,frieren,darkness}\`

Prior chosen epochs (archive): Fern e008, Frieren e006 — files ~170 MB (≈ **rank 32** SDXL). Darkness same size, installed at `Lora\Darkness\Darkness.safetensors`.

## Caption strategy (identity, not style fight)

**Do not** train on trigger-only or trigger+traits alone (absorbs pinup gloss into the LoRA).

Per image:

```
{trigger}, {identity traits}, {pose}, {outfit}, {background}, {art style / lighting tags}
```

- Trigger first; traits always present.
- **Describe** pose / outfit / bg / style so they are *not* the character.
- Darkness hard negatives in captions when visible: `human ears, no pointy ears` (scene_match showed elf-ear bleed).
- Caption dropout in trainer: **0.05–0.10** (keep trigger+traits rate high if your UI supports keep tokens).
- Skeleton captions currently end with a placeholder phrase — **replace via WD14 / JoyCaption / manual** before train (`scripts/rebuild_id_captions.py`).

### Trait packs

```
nb_fern, 1girl, purple hair, long hair, bangs, purple eyes, flower hair ornament, medium breasts
nb_frieren, 1girl, white hair, long hair, twintails, green eyes, pointy ears, elf, small breasts, red earrings
nbk_darkness, 1girl, blonde hair, long hair, ponytail, blue eyes, large breasts, x hair ornament, red hair ornament, human ears
nb_ubel, 1girl, short black hair, purple eyes, black clothing
nb_flamme, 1girl, elf, blonde hair, long hair, green eyes, pointy ears
nb_cha_hae_in, 1girl, blonde hair, short hair, bangs, yellow eyes
nb_jinah_sung, 1girl, purple hair, medium hair, purple eyes
nb_joo_hee, 1girl, brown hair, glasses
```

### Caption style bucket (rest train / preferred)

Do **not** stamp `soft lighting` on every image (binds one lighting look to the trigger). Use:

```
anime illustration, detailed background, natural skin texture, lineart visible
```

…plus WD14 pose / outfit / bg / **real lighting** tags so lighting stays in the caption, not the LoRA.

## Train recipe (kohya sd-scripts / kohya_ss GUI)

Base: **Illustrious / waijfu training base** (same family as current cast LoRAs — do not mix Pony).  
No checkpoint merge.

| Knob | Value |
|------|--------|
| network_dim (rank) | **16–32** (start **32** to match ~170 MB lineage; try **16** if style still sticks) |
| network_alpha | dim/2 (16 if dim=32) |
| lr | 1e-4 unet / 5e-5 text encoder (or TE off if ID-only and TE was unused before) |
| scheduler | cosine / cosine_with_restarts |
| resolution | 1024 (bucket) |
| batch | 2–4 (VRAM) |
| repeats | ~10–20 → ~1.5k–3k steps/char |
| epochs | **4–8**; save every epoch; prefer **earlier** than old e008 if overfit/style |
| caption_dropout | 0.05–0.10 |
| noise_offset / min_snr | optional house defaults |
| flip_aug | on (portraits); off if asymmetric hair ornaments break |

### Output paths (do **not** overwrite until validated)

```
D:\StabilityMatrix-win-x64\Data\Models\Lora\Fern\Fern_id_v1.safetensors
D:\StabilityMatrix-win-x64\Data\Models\Lora\Frieren\Frieren_id_v1.safetensors
D:\StabilityMatrix-win-x64\Data\Models\Lora\Darkness\Darkness_id_v1.safetensors
```

Also keep epoch dumps: `Fern_id_v1-e002.safetensors` etc.

### Validation smoke (waijfu only)

1. Solo portrait each trigger @ 0.6 / 0.8 / 1.0 — face lock vs style bleed.  
2. 2-girl Fern+Darkness — **no elf ears on Darkness**.  
3. Nude bedroom still — style should match waijfu, not training-set gloss.  
4. Then re-run one scene_match hard pose **with** pose LoRA (not as ID test).

## Toolchain unblock

Install on **ComfyBox** (GPU):

1. [bmaltais/kohya_ss](https://github.com/bmaltais/kohya_ss) **or** [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)  
2. Point dataset dirs at `D:\studio-agent\training\id_lora_v1\...` (or `/mnt/...` mount)  
3. Run WD14 pass → train three chars sequentially  
4. Copy `*_id_v1.safetensors` into Stability Matrix Lora folders above  
5. Point catalog / tests at new files only after smoke

Main-rig CPU torch **cannot** train these.

## Pose LoRA (separate — Illustrious)

Find (prefer download IL versions):

| Need | Candidate | Notes |
|------|-----------|--------|
| Facesit POV | `[Close-up] Facesitting` → `se_v1_facesitting.safetensors` (IL) | Local `povFacesitting.safetensors` is likely **Pony** — verify base before stacking on waijfu |
| FFM top + oral | `FFM threesome - Straddling and Fellatio (Illustrious)` | Trigger `ffm_threesome_1st_girl_on_top` / straddling_fellatio |
| 69 | No clean dedicated IL 69 LoRA found | Train pose-only **or** OpenPose from keeper stills |
| Strap-on | Not in house NSFW catalog | Concept LoRA or OpenPose+ref |

**Pose-only train (if creating):** varied faces/bodies/outfits; **strong pose tags + unique trigger**; weak/no identity; rank 8–16; 40–80 images per pose concept; caption identity sparsely so pose binds to trigger.

House NSFW still catalog (`list_nsfw_image_loras`) has **style** LoRAs only (manga/NTR/fantasy) — **no** oral/facesit/69 still concepts registered.

## Deepthroat full-hilt

| Layer | Recommendation |
|-------|----------------|
| Prompt-only | Caps ~80–90% insert on waijfu; use spatial tokens (below) |
| Still concept LoRA | Download IL **Deep Throat Diffusion** / hard irrumatio generators; train house `nb_fullhilt_dt` on full-hilt stills if downloads underperform |
| Wan (video) | Already local: `wan2.2-i2v-*-oral-insertion-v1.0` + `wan22-ultimatedeepthroat-*` — **motion**, not still scene_match |
| Do not | Expect char ID LoRA retrain to teach full-hilt |

### Still prompt recipe (waijfu + oral concept LoRA @ 0.6–0.85)

Positive (after quality/style/view):

```
deepthroat, irrumatio, penis all the way in, nose pressed against stomach, balls on chin, throat bulge, lips sealed at base of penis, no gap, facefuck
```

Negative:

```
partial insertion, tip only, licking, kissing tip, gap between lips and base, short penis, oral tease
```

House fluids policy: only add cum/after-oral if asked (`after oral` LoRAs are a different beat).
