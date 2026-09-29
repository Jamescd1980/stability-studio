# Nari document index

Start here when you need house rules, Wan recipes, or storyboard text.

Use MCP tools (preferred):

- `list_studio_docs` — catalog of readable `.md` / `.txt`
- `read_studio_doc(doc="<id>")` — load by id below
- `search_studio_docs(query="…")` — grep allowlisted docs
- `lookup_character_identity(name="Eris")` — LoRA vs **baked into waijfu**

## Doc ids

| id | What |
|----|------|
| `prompting` | **Do/Don't → pos/neg** + lexicon (**gold standard** = lane/LoRAs, not prompt text) |
| `lessons-wan-i2v` | Wan 2.2 MoE keepers, action LoRA bundles |
| `lessons-nsfw-stills` | Still recipes, gold finish, waijfu notes |
| `lessons-comfybox-cuda` | ComfyBox GPU / labor split |
| `lessons-set-fill` | Mesh / locked plates |
| `lighting-agents` | Lighting + **waijfu bake** notes (Frieren etc.) |
| `das-booty-beats` | TheaterJobs Das Booty beat list |
| `hardware` | Nari / Myra / Orla / Eric map |
| `nari-skill` | This agent's OI skill |
| `agents` | Repo AGENTS.md |

## Character identity (important)

- **`waijfu` / `waijfu_alpha`** already knows **many popular anime faces**, including **Eris Greyrat** (and Frieren is noted as baked — keep dedicated Frieren LoRA ≤ ~0.50 if stacking).
- Call `lookup_character_identity` / `resolve_character_loras` before inventing a missing-LoRA failure.
- Dedicated catalog LoRAs (Fern, Frieren, Darkness, Solo Leveling cast, …) still win for tight ID lock when present.

## Host policy

All create / Forge refine / Wan on **ComfyBox** unless the user says otherwise.
