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

- Prefix injected: `masterpiece, best quality, amazing quality, anime illustration`
- You write only the **add-on** Positive (subject, act, view, light, tails you intentionally want).
- **Never** re-type the prefix into Positive. Quote it in Notes so the human sees what the model will get.
- If the human says “don’t use anime,” that conflicts with the waijfu prefix — say so and pick another style or note that a prefix override is required.

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

## Positive prompt = Do’s

Put only what should appear or happen:

1. Quality / aesthetic line (or rely on style `prompt_prefix`)
2. Subject / identity triggers (character LoRA triggers, hair, eyes)
3. Pose / act / props that belong in frame
4. Setting + light
5. Framing with **View …** when needed
6. Optional short style line (`anime++`, cel-shade) if the checkpoint wants it

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

Put only what should **not** appear:

- Anatomy fails the style already lists (`bad hands`, `deformed`, …)
- PIP / inset / collage if the user hates panels
- Unwanted people, props, or styles (`photorealistic` on anime, etc.)
- Lane `negative_extra` from gold_standard / look profiles (merged by tools — don’t retype the mood name)

Keep negatives **short**. Do not dump every possible anti-tag.

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
