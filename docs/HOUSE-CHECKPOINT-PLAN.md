# House checkpoint plan — Theater Jobs / Galleria

**Date:** 2026-08-10  
**Status:** Plan only for merge. Preference LoRA `house_pref_IL` trains first. **v4** (mild S1 bake) may cost waijfu gold finish — see [`LIGHTING-AGENTS.md`](LIGHTING-AGENTS.md).

## What we already have

| Asset | Role | Use / don't |
|---|---|---|
| `waijfu_alpha` | Primary NSFW anime stills; Frieren baked; girls-only cleaner | **Base** of house ckpt |
| `waijfu_house_v1` | Bake of S1@0.7 + `anti_sprawl`@0.75 into waijfu | Legacy; **avoid for strip keepers** (S1 silhouette halo) |
| `waijfu_house_v2` | Bake of `house_pref_IL`@0.7 into waijfu (no S1) | Soft house stills; keep for A/B |
| `waijfu_house_v3` | Bake of `house_pref_IL`@**1.0** into waijfu (no S1) | PIP-hard; no extra window/S1 |
| `waijfu_house_v4` | `house_pref`@1.0 + `anti_sprawl`@0.45 + S1@**0.28** | **Demoted** — Invoke 2026-08-11: giant window inversion. Catalog `waijfu_house` → **v3** |

**Owner delivery (this Windows rig):** Forge + Invoke only — ship keepers to `D:\Extra Models\Waifu\` (and LoRAs under `D:\Extra Models\` / `LoRa's`). Do **not** treat local Stability Matrix / ComfyUI as the user install path. ComfyBox SM paths are for remote agent gens only.

| `reedXXXIllustrious_v150` | Stronger sex contact / oral / 69 | **Merge donor** for contact UNet layers |
| `anti_sprawl_IL` | Prefer plain walls / dim / no window-lamp invent | Keep as LoRA **or** bake light into house v2 |
| `house_pref_IL` (new) | Broader prefs: anti-PIP/panels + anti-sprawl + single-frame | Default stack LoRA; candidate bake for house v2 |
| `Darkness_sliderFin3` | Dim mood (ComfyUI) | **Never bake**; **Invoke: ineffective** — use dim prompt tags (see LIGHTING-AGENTS.md) |
| Cast ID LoRAs (`Fern_id_v1`, `Frieren_id_v1`, `Darkness_id_v1`) | Identity | Keep LoRA; Frieren ≤0.50 on waijfu |
| Eyes / ILDetailer / S1 | Beauty / lighting | Stack at gen time; do **not** bake S1 into sex house (halo) |
| Catalog (often remote): `ilustmix`, `anime`/`waiIllustrious`, `noobai_vpred` | Face beauty / pose / full-body | **Not** merge parents for NSFW house — lane-switch at gen |
| `perfection25DILXL…_33` | Stub **0 bytes** on Windows SM | Ignore until restored |
| `divineelegancemix_V10` | Non-IL elegance mix | Skip for Illustrious house |

Phase 0 baselines: `docs/MERGE-WAIJFU-REEDXXX-phase0.md`  
Takeaway: **waijfu** = ID + girls-only; **Reedxxx** = contact; **both** invent windows/lamps.

---

## Preference LoRA (`house_pref_IL`) — covers what one LoRA can

| Problem | Covered? | How |
|---|---|---|
| Unprompted windows / trees / sun / lamps | Yes | anti_sprawl preferred + night BG keepers |
| PIP / panels / collage / inset | Partial→Yes | Captions + approved single-frame CGs |
| Plain closed rooms | Yes | BG + asprawl |
| Dual character ID bleed | No | Cast LoRA weights + later facesit bake |
| Facesitting / 69 pose obedience | No | Separate IL pose LoRA or bake later |
| Hard contact / oral anatomy | No | Reedxxx merge |
| Bad hands | Weak | Negatives + detailer; not this LoRA |
| Frieren overbaked when LoRA high | No | Cap Frieren ID ≤0.50 |

**Trigger:** `housepref`  
**Default weight:** 0.65–0.85 on `waijfu`  
**Train base:** `waijfu_alpha` (same as anti_sprawl)

Usage: put `housepref` in positive; keep short neg with `picture in picture, panels, collage, window, trees` when those are unwanted.

---

## House checkpoint roadmap

### Phase A — Preference LoRA (now)

1. Assemble `assets/house_pref_dataset/` (anti_sprawl + Wild Fern / Water Closet keepers + night BGs).
2. Stage + Kohya train → `Lora/house_pref_IL.safetensors`.
3. A/B gate vs bare waijfu on fixed seeds (PIP prompt, closed-room night, dual yuri).
4. If gate passes, default-stack in house gen scripts; keep `anti_sprawl_IL` optional (overlap OK at lower weight).

### Phase B — Contact merge (house_sex_v1)

**Goal:** One Illustrious NSFW ckpt that keeps waijfu identity/girls-only and borrows Reedxxx contact.

| Step | Action |
|---|---|
| B0 | Confirm both ckpts on ComfyBox mount (full size, not 0-byte stubs) |
| B1 | Weighted sum merge (Comfy ModelMerge / kohya) — start **UNet-biased** Reedxxx ~0.25–0.35, CLIP mostly waijfu |
| B2 | Re-run Phase 0 pack + FD01–04 doggy/oral/69/facesit baselines **no cast LoRAs** |
| B3 | Pick keeper ratio; save `waijfu_reed_contact_v1.safetensors` |
| B4 | Do **not** bake Darkness slider or S1 |

**If Reedxxx male/cock leak worsens facesit:** lower Reed ratio or mask merge to mid/late UNet only.

### Phase C — Preference bake (house_v2)

Bake into contact merge (or plain waijfu if B slips):

| Bake | Ratio (start) | Notes |
|---|---|---|
| `house_pref_IL` | 0.6–0.75 | Prefer over re-baking old anti_sprawl alone |
| Skip S1 | — | Stack S1 at runtime when needed |
| Skip Darkness slider | — | Always LoRA |
| Skip cast IDs | — | Always LoRA |

Output: `waijfu_house_v2.safetensors` — catalog style `waijfu_house` points here after gate.

### Phase D — Pose prior (optional, later)

- Train or download **IL** facesitting / 69 concept (never Pony on IL).
- A/B as LoRA first; bake only if weight is always ~same and identity holds.
- Same for doggy if Reed merge still weak on rear roles.

### Phase E — Negative embed (optional)

Train a small **TI / neg embed** `tj_bad` on: PIP, panels, trees-in-window, lamp spam, male hand on yuri. Faster than another LoRA for “always off” vices.

---

## What other checkpoints help (without merging them in)

| Checkpoint / style | Help for | How to use |
|---|---|---|
| `reedXXX` | Sex contact donor | Merge Phase B |
| `ilustmix` | Dialogue / face beauty | Style lane, not merge |
| `anime` / WAI Illustrious | Pose-heavy / combat | Style lane + ControlNet |
| `noobai_vpred` | Full-body / tag obedience | Layout pass before waijfu beauty |
| `juggernaut` / photo plates | Empty set plates | BG only |
| Pony / `merged_dreams` | Fantasy romance | Separate lane — **do not** stack Pony LoRAs on waijfu |
| `homochi` | Male-focus | Rare; not house default |
| `miracle_nsfw` (Flux) | One-off prose NSFW | Not Galleria continuity |

---

## Explicit non-goals

- Do not bake Darkness body / slider into ckpt.
- Do not download Pony facesitting onto Illustrious.
- Do not use `waijfu_house_v1` (S1-baked) as the sex contact merge base — start from `waijfu_alpha` + Reed, then bake `house_pref`.
- Do not treat preference LoRA as a fix for dual-ID or facesit geometry.

---

## Success gates

1. **LoRA:** same seed, prompt without `window`/`PIP` — fewer windows + zero PIP vs baseline.
2. **Merge:** Phase 0 P02/P04 contact clearer than waijfu alone; P01 Frieren still recognizable without cast LoRA; yuri pack does not invent cock more than Reed alone.
3. **House v2:** passes (1)+(2) with fewer stacked LoRAs (pref baked; S1/Darkness/cast still external).
