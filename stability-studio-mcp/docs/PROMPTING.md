# House prompting — Do / Don't / lexicon

**Audience:** Nari, Jan, Cursor, One Desk agents writing Platform / Positive / Negative for Comfy or Forge.

**Hard split**

| Human / agent language | Goes into |
|------------------------|-----------|
| **Do** (what you want to see) | **Positive prompt** (`prompt` / `prompt_positive`) |
| **Do not** / avoid / anti-tags | **Negative prompt** (`negative_prompt` / `prompt_negative`) |

Never put Do-not language in the positive. Never put “please draw X” coaching essays in either field when tag/grammar styles expect compact tags.

Call `get_prompt_style(style=…)` or `get_prompt_style(platform=…)` before drafting. Call `compile_image_prompt` if the positive got verbose.

---

## Two workflows (Desk Prompt lab ↔ Image gen)

| Mode | Where you work | What you produce | Image gen consumes |
|------|----------------|------------------|--------------------|
| **Pre-planned** | Dedicated prompt/storyboard `.md` (e.g. `prompts/<scene>.md`) — **not** `AGENT.md` | Beat list of stills for one scene; each numbered block is a full pack | Human points at block `01` / `02` / … — agent gens from that block |
| **Free-style** | Live chat in **Prompt crafting** only | One pack hammered in conversation until “done” | Human pastes or confirms the FINAL pack in **Image generation** |

**`AGENT.md` is the project key** (where-left-off / decisions / character-locks). Never put Platform/Positive/Negative packs there.

**Pre-planned:** prompt file is source of truth; chat is for decisions. Typical beat list: establish → beat → climax. Each block = Platform/style | Positive (add-on only) | Negative | LoRAs | Notes.

**Free-style:** no file; iterate in chat; summarize FINAL pack and switch jobs.

Ask which workflow if the human does not say. Same Do/Don’t, auto-inject, and lexicon rules apply to both.

---

## Auto-inject (both Prompt lab and Image gen must know this)

`generate_image(style=…)` **always prepends** that style’s `prompt_prefix` and merges the style’s default `negative_prompt` (plus any lane `negative_extra`).

Example for **waijfu**:

- Prefix injected for Illustrious / WAI styles: `masterpiece, best quality, amazing quality, very aesthetic, absurdres, ultra-detailed`
- You write only the **add-on** Positive (accepted style tags, then lighting, character, pose, background).
- **Never** re-type the prefix into Positive. Quote it in Notes so the human sees what the model will get.
- The low-light tag is `low key`.
- Style tags are not in the prefix. Ask, explain each in one sentence, and add only the ones the user accepts: `anime illustration` (the picture is an anime drawing), `anime style` (harder anime medium), `anime++` (sharper anime faces and flatter color), `bold outline` (thicker ink), `cel-shaded coloring` (hard shadow shapes; changes the mouth and the lighting).
- Eye LoRA triggers such as `perfect eyes` stay when that LoRA is on. They are not part of the style ask.

`resolve_style_lane("gold standard")` adds **LoRAs + prompt_tail + negative_extra** via tool args — still never write the words “gold standard” into the prompt.

---

## Lexicon (studio speak ≠ model text)

These phrases are **house workflow labels**. They select checkpoints, LoRA stacks, negatives extras, and settings via MCP (`resolve_style_lane`, look profiles, catalog moods). **Never paste them into Positive or Negative** for Forge/ComfyUI — the model will try to draw the words.

| Term | Means | Do this | Never do this |
|------|--------|---------|---------------|
| **gold standard** / **gold_standard** / **detail hero** / **recreate 003** | Mood + look profile: `resolve_style_lane("gold standard")` → usually `waijfu` + `illustrious_detail_hero` (Eyes / ILDetailer / finish LoRAs + `prompt_tail` / `negative_extra`) | Resolve lane, attach LoRAs + settings, use the lane’s prompt_tail/neg extras | Write `gold standard`, `detail hero`, or `recreate 003` in the diffusion prompt |
| **look profile** | Named LoRA/neg stack in the catalog (e.g. `illustrious_detail_hero`) | Pass via style lane / generate args | Prompt the profile id as text |
| **style** / **food_group** / **platform** | Catalog routing (`ilustmix`, `pony`, `anime`, …) | `generate_image(style=…)` | Dump style ids into the positive unless they are real tags the checkpoint expects |
| **keeper** | Quality bar for a still/clip we keep | Gate + approve | Prompt `keeper` |
| **Prepare Wan** | UI/backend ready step | Confirm in Desk / MCP checks | Prompt `prepare wan` |
| **View** (framing) | POV / angle wording in the **positive** (`View from mans POV`) | Use as a framing phrase | Say **camera** (spawns camera props) |

If the user says “make it gold standard,” that is an instruction **to you** (agent): apply the gold lane. It is **not** a caption for the image model.

---

## Grammar by family

One grammar does not fit every checkpoint. Call `get_prompt_style` and follow that style’s family. Do not paste Illustrious tags into Flux, or Flux sentences into Illustrious.

**Illustrious / anime SDXL** — `unholy_desire` (launch), `thumbs_up`, `ilustmix`, `animagine_xl`, `aom2`, `homochi`, `perfection_25d`, `noobai_vpred`, and the off-page WAI checkpoints.

- Comma tags. The quality line is auto-injected. Do not retype it, and do not move the subject in front of it.
- After the prefix: accepted style tags, lighting, character, pose, background.
- Negatives stay. Keep them short.
- Do not say `camera` (it draws a camera). Use `View …` for framing.
- A weight such as `(tag:1.2)` only when one tag must beat another. Do not weight the whole prompt.
- `unholy_desire` stays at steps 16, CFG 2.5, DPM++ 2M Karras. `thumbs_up` stays at steps 28, CFG 6, euler ancestral.

**Pony SDXL** — `pony`, `merged_dreams`.

- `score_9, score_8_up, score_7_up` first (the style prefix). Put `score_6` and below in the negative.
- Short comma phrases after the score line. Not a Danbooru tag wall, and not a Flux paragraph.

**Photoreal SDXL** — `juggernaut`, `realisian`, `realvis_xl`. `n4mik4` is Illustrious-family cyber, not this group.

- Subject first, then action, setting, light.
- Negatives yes. Camera and lens words are allowed here.
- Do not use the Illustrious quality line.

**Flux** — `miracle_nsfw` only (Flux.2 Klein). `juggernaut` and `merged_dreams` are not Flux.

- Full sentences. Subject, then action, then style, then context. Put the important part first.
- About 30–80 words. No negative prompt. Leave `negative_prompt` empty.
- Camera, lens, and lighting language is correct on Flux.
- Do not send `masterpiece, best quality` or Danbooru tags.

Public sources for this split: Black Forest Flux.2 prompting guide (no negatives, subject then action then style then context, word order) and the usual SDXL tag-and-negative practice. Illustrious keeps the trained quality line first. That part is ours, and it should not be replaced by the Flux order.

## Positive prompt = Do’s (Illustrious)

Put only what should appear or happen:

1. Quality line — rely on style `prompt_prefix` (do not retype it)
2. Style tags the user accepted (`anime illustration`, `anime style`, `anime++`, `bold outline`, `cel-shaded coloring`) — ask first; do not add them on your own
3. Lighting (`low key` when the light is low)
4. Character / identity triggers (character LoRA triggers, hair, eyes)
5. Pose / act / props that belong in frame
6. Background / setting
7. Framing with **View …** when needed

**Do**

- Name one act once (`blowjob`, `doggystyle`, `missionary`)
- Keep it short; one job per phrase
- Use vulgar sex terms when the scene is explicit (see `.cursor/rules/nsfw-sex-prompting.mdc`)
- Put eye color / hair / markings you want **in the positive** (and in Forge `face_prompt` when refining)

**Do not put in positive**

- Anti-tags (`bad hands`, `blurry`, `lowres`) — those are negatives
- Studio jargon from the lexicon table above
- Synonym stacks for the same act
- Anatomy coaching (`perfect hands`, `correct limbs`) — prefer negatives or let detail LoRAs handle finish

---

## Negative prompt = Don’ts

Scene don’ts go after the basic block. Do not drop the block to keep the line short.

Basic block for Illustrious, Pony, and photoreal SDXL. Always keep it:

`bad hands, poorly drawn hands, extra fingers, missing fingers, fused fingers, deformed fingers, mutated hands, extra limbs, bad anatomy`

Then add only the scene:

- PIP / inset / collage if the user hates panels
- Unwanted people, props, or styles (`photorealistic` on anime, etc.)
- The style’s own quality line (`bad quality`, `worst quality`, watermarks, `score_6` on Pony)
- Lane `negative_extra` from gold_standard / look profiles (merged by tools — don’t retype the mood name)

`generate_image` merges the style negative with the negative you pass, then puts any missing basic tag back. Flux (`miracle_nsfw`) has no negative. Leave it empty.

---

## Gold standard (definition)

**Gold standard** = the house **finish recipe**, not a look you spell into the model.

- Catalog mood: `gold_standard` (aliases: gold standard, detail hero, park heejin bar, recreate 003)
- Typical resolve: `default_style: waijfu`, `look_profile: illustrious_detail_hero`
- Applies: checkpoint/style choice, detail LoRAs (eyes / ILDetailer / night sliders as configured), `prompt_tail` quality chips, `negative_extra` for plastic/muddy/oversmooth
- Agent path: `resolve_style_lane("gold standard…")` → generate with returned style + LoRAs; merge prompt_tail into **positive** tags and negative_extra into **negative** — still never write the words “gold standard”

---

## Quick template

```text
Platform: illustrious | pony | flux | …
Positive: <do’s — scene, subject, act, view, light>
Negative: <don’ts — anti-tags only>
Settings/LoRAs: <gold standard lane / character LoRAs — tool args, not prompt text>
```

---

## Launch checkpoint

Anime launch style is `unholy_desire` (Unholy Desire Mix v9, file `unholyDesireMixSinister_v90.safetensors`).

- Style id: `unholy_desire`
- Steps 16, CFG 2.5, sampler DPM++ 2M Karras (the style defaults). Do not raise CFG to 7 unless they ask.
- Optional tokens, one only, when they want the sinister look: `unholy-aesthetic` or `unholy-detailing`
- Do not stack the SDXL Lightning LoRA
- Illustrious outfit LoRAs such as armored dress still stack on this checkpoint

**Thumbs Up** is also on the anime shelf. Style id `thumbs_up`, file `thumbsUpIllustrious_tuI2V12.safetensors` (Tu-i2 v1.2). Use it when they name Thumbs Up. House Illustrious defaults: steps 28, CFG 6, euler ancestral. Do not replace the launch style unless they ask.

## Outfit LoRAs

Clothing LoRAs are catalog `outfit_loras` (also returned by `get_generation_context`). They are not character identity. Stack them beside a character LoRA when both apply.

**Armored dress** (Illustrious, Civitai model 92654, version 1890497)

- File: `armored_dress_IL.safetensors`
- Trigger in the positive: `armored_dress`
- Weight: `1`
- Style: `unholy_desire`
- Add `plate armor` or `scale armor`, and `Surcoat` or `Tabard`, only for the pieces they named.
- Call: `generate_image(style=unholy_desire, loras=[{"file": "armored_dress_IL.safetensors", "weight": 1}], prompt includes armored_dress)`
