# scene_match_comfy / v2 — blame table

Date: 2026-07-26  
Folders: `D:\ComfyBox Images and Videos\Images\scene_match_comfy\` (10) and `scene_match_comfy_v2\` (12)  
Cross-check refs: `Images\merge_phase0_baselines\fern_darkness_smoke\waijfu\` (FD01–FD04). `Images\Girls 3 some\` is **empty**.

## Verdict

Failures are mostly **composition / act / prop** (strap-on, 69, facesit, 3-girl oral pile), not “wrong hair color.” Character LoRAs give hair/eyes but **bleed identity** under multi-girl load; they also appear to carry **gloss/plastic style** that fights waijfu. Retrain for **identity/comp only** is justified; it will **not** fix facesitting/69/strap-on geometry by itself.

## Blame table

| Shot | Main fail | ID | Style fight | Lighting | Act / roles | Strap-on |
|------|-----------|----|-------------|----------|-------------|----------|
| v1 FD01 strap doggy | Harness/straps mush; insertion missing; glossy skin | Fern/Darkness hair OK, faces generic | Heavy wet/plastic sheen | Harsh window bloom | Roles muddled (not clean doggy fuck) | **Fail** — thin straps / purple blob, no usable dildo |
| v1 FD02 facesit | Not a clean facesit; limb merge | OK-ish hair | Gloss | Flat bright bed | Facesit → half-69 mush | n/a |
| v2 FD_strap_A (D→F) | Pipe-like black cylinders; body merge; inset crop artifact | Hair/eyes OK | Style + anatomy melt | Dim wood room + giant bg dildo distraction | Doggy intent lost | **Hard fail** — disconnected pipes |
| v2 FD_strap_B (F→D) | Harness visible but no contact/insert; blown backlight | Fern top / Darkness bottom readable | Soft washed silhouettes | **Overexposed** rear light | Roles clearer than A; act still fake | Partial — harness yes, fucking no |
| v2 FD_facesit_A | Sitting/lick, not facesit; leg merge | Darkness gets **elf ears** (Frieren bleed) | Homogenized eyes | Soft lamp | Wrong act; roles flipped vs filename intent | n/a |
| v2 FD_69 | Impossible bridge pose; oral on purple blob | Generic faces | Extreme oil sheen | Warm side light | 69 anatomy collapse | Purple organic blob as “toy” |
| v2 FD_facelick | (same family as v1) shallow contact | ID soft | Gloss | — | Facelick shallow | n/a |
| v2 G1 cheek lick + finger | 3 IDs by hair only; arms vanish | Darkness ≠ Konosuba face lock | Plastic Illustrious homogenization | High-key flat | Act OK-ish (simple); genitals mush | n/a |
| v2 G2 kissing pile | Torso blend; Fern arm wrong | Readable hair, generic faces | Airbrushed | Bright wash | Kiss pile OK structurally, contact weak | n/a |
| v2 G3 dual oral legs-up | Hip/leg detach; oral zone mush | **Darkness elf ears** again | Doll skin | Clean overhead | Dual oral intent; anatomy fail | n/a |
| v2 G4 tongues over pussy | Contact mush (vision later unavailable) | Same multi-LoRA bleed risk | Same | — | Complex oral stack underspecified | n/a |

## Root causes (ranked)

1. **Hard poses without pose LoRA / ControlNet** — facesit, 69, dual oral, strap doggy exceed base + char LoRA.
2. **Strap-on is a prop concept** — needs dedicated still LoRA or ref+i2i/OpenPose; char LoRAs invent pipes/blobs.
3. **Multi-character LoRA stack** — ear/eye bleed (Darkness←Frieren); identical purple eyes.
4. **Style-coupled char LoRAs** — train sets are glossy pinups; captions likely did not “explain away” style → plastic fight with waijfu.
5. **Lighting prompts** — bright window / bloom washes contact edges (strap_B especially).
6. **Girls 3 refs folder empty** — scene_match had no pixel target for G* shots.

## What retrain will / won’t fix

| Will help | Won’t fix alone |
|-----------|-----------------|
| Cleaner Fern/Frieren/Darkness under waijfu | Facesit / 69 geometry |
| Less style fight (if captions style-neutral) | Strap-on harness + insertion |
| Less ear bleed if Darkness captions stress **human ears, no pointy ears** | 3-girl oral pile anatomy |
| Better face lock at 0.6–0.8 weight | Full-hilt deepthroat (needs oral concept LoRA) |
