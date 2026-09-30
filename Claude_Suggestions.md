# Suggestions — One Desk + Stability Studio MCP (planning)

Planning and idea refinement for **private** development and an eventual public release. Not a ship schedule — see `Product_roadmap.md`.

Written by Claude (Opus), 2026-09-29, after the five OneDesk fix batches (see `desk-ui/CODE_FIX_HANDOFF.md` in the One Desk repo, or this monorepo’s ignored `desk-ui/` checkout). Updated the same day after Owner feedback. Extended with Owner + Build AI roadmap grammar, big-picture phases, Editing-as-teaser, and Build AI answers to §18.

Each idea says where it came from:

- **Owner** — your idea or decision.
- **Claude** — my suggestion.
- **Build AI** — Composer / build lane feedback.
- **Both / All** — shaped together.

## How we use the three docs (Owner, 2026-09-29)

| Doc | Role |
|---|---|
| **`Claude_Suggestions.md` (this file)** | Conversation and idea refinement. Non-coding communication. Hash things out here while they are fresh. Not a schedule. |
| **`Product_roadmap.md`** | Final plan for each **Phase / Step / Batch**. The next Phase is the active target. Focus on what is in front of us. |
| **`desk-ui/CODE_FIX_HANDOFF.md` (and similar handoffs)** | Work that has been designed or coded and needs **implementation and/or verification**, with human-in-the-loop testing. |

Ideas may land here during renders, tests, or while one AI is coding. What sticks gets promoted into `Product_roadmap.md`, then into handoff batches when we build.

**Grammar (Owner + Build AI):**

| Word | Scope | Example |
|---|---|---|
| **Phase** | Big picture — product era / release story | Phase 1 = first public beta |
| **Step** | Medium picture — workstream inside a phase | Step: resizable chat; Step: guided tour |
| **Batch** | Small picture — shippable engineering slice | Batch 6 = Storyboard/FLF UX |

Rule: Phases get marketed; Steps get planned; Batches get coded and verified. Do not call a Batch a Phase in the handoff, or a Phase a Batch in the public roadmap.

Open questions for Owner remain in **section 14**. Living roadmap: **`Product_roadmap.md`**.

---

## 1. Decisions already made

| Decision | From |
|---|---|
| No auto-update. Manual updates first, with a way to roll back to the previous version. | Owner |
| Ship a third-party notices file. | Both (Claude suggested it, Owner approved) |
| The only outside program the docs recommend users run themselves is **Krita**, for freehand painting and custom inpainting. | Owner |
| If a program has working code, **keep it but separate it** by program, not scrub it. | Owner |
| **No dead parts.** Nothing stays in the build that no longer works because it was scrubbed or abandoned. | Owner |
| Stability Matrix and Wan2GP are unnecessary for a dual-PC build but good for a single-PC build. Wan2GP uses VRAM more efficiently than ComfyUI. | Owner |
| Docs say **"ComfyUI, any install"** instead of requiring Stability Matrix. | Both (Claude suggested, Owner approved) |
| **NSFW stays hidden in One Desk** unless the user turns it on. | Owner |
| A **basic DaVinci-inspired video and audio editor** is designed in detail (section 12) as the **coming-next teaser** and Phase 2 backlog — **not** required for first beta. First release uses **existing AI-only splice/mix tools**, not a manual Editing UI. | Owner (scope cut); Claude (full design); Build AI (agree teaser / Phase 2) |
| Timeline / audio nudge / MP4 vs WebM / Combine-Split / agent “show me the splice” designs stay documented in section 12 for later. | Owner + Claude |
| **Ren'Py / WebM game export is secondary.** Primary: AI-driven art, MCP, One Desk UI. | Owner |
| **Resizable / collapsing chat panel** (enlarge viewer) ranks **above** the manual editors for near-term UI. | Owner (priority); Claude (design §7.1); Build AI (agree) |
| **Phase / Step / Batch** grammar for planning (see above). | Owner + Build AI |
| Docs roles: Suggestions = ideas; Product roadmap = final plan; Handoff = implement + verify + human test. | Owner |
| Ship **One Desk** and **MCP** as the two first-party boxes; ComfyUI, Forge, Wan 2.2, Krita (and Comfy vs Stability Matrix) left to the user with soft guidance from local hardware. | Owner |
| Point users to **headless ComfyUI + One Desk** for AI-driven workflows, and **Krita** for human-driven paint — both can share headless Comfy; agent manages workflows, checkpoints, LoRAs, and prompt paste. | Owner |
| Blender tools may stay in MCP early; **do not surface in One Desk UI** until Phase 2 readiness. | Owner |
| Divide big upgrades into **small batches** and proof each; avoid one mega-land that takes a week to unbreak. | Owner + Build AI |
| Guide / teaser clip: rebuild simply from **bow + breeze + footsteps + JP hello on bow** (lost full Rin splice was posted to X; don’t block on recovering it). | Owner |
| Encoding / save progress bar when long ffmpeg encodes land. | Build AI (agree); Claude (noted in §12) |
| Fresh-start project folders for end users (section 13). | Owner |
| Guide sample = the **original Rin** example family (bow-focused rebuild OK). Ducking starts at **6 dB** when audio editor ships. | Owner |
| Publish a **compatible programs list**, and let the agent read the same list. | Owner |
| **Krita hand-off** conversation (section 4). | Owner |
| READMEs for both the MCP and One Desk need a clean-up. | Owner |
| `D:\Extra Models\` is the owner's Invoke canvas test bench, not an app install target. | Owner |
| One Desk came out of writing a book and hitting real problems. Writing features stay first-class. | Owner |

---

## 2. Separation by program ("program packs")

**Idea:** Owner (separate by program, no dead parts). **Design:** Claude.

### The problem

The MCP has 100 tools in one `server.py`, and all of them load whether or not the program behind them is installed. On a dual-PC build, Wan2GP tools show up even though Wan2GP isn't there. Every unused tool is also one more wrong choice for a small local model.

### The design

Every program the MCP talks to becomes a **pack**: its tools, its health check, its config section and its docs page, grouped together.

| Pack | What it covers |
|---|---|
| `comfyui` | Image, edit and video generation (any ComfyUI install, local or remote) |
| `forge` | Face refine and global refine |
| `wan2gp` | Hero I2V and lip sync (single-PC) |
| `stability_matrix` | Model folder layout preset only. It's a launcher and model manager, not something the MCP drives. |
| `krita` | Open image in Krita, report models, write Krita styles (section 4) |
| `ollama` | Local brains (Nari prompt enhance, unload before GPU work) |
| `kokoro`, `moss` | Speech and sound |
| `post` | ffmpeg splice, RIFE, SeedVR polish |
| `blender` | Pose and depth map bridge |
| `files` | Media listing, viewing, rename, recycle |

**How a tool gets loaded.** Each tool is tagged with its pack (and whether it's adult-only, section 5). At startup the MCP registers a tool only when:

1. its pack is turned on in `config.yaml` (`programs: {wan2gp: false, ...}`),
2. its pack fits the chosen **layout**, `single_pc` or `dual_pc`, and
3. it isn't adult-only while adult content is off.

That is one small wrapper around the existing `@mcp.tool` decorator. The tools themselves don't need rewriting.

**Layouts.** The two layouts are presets, not separate code:

- **`single_pc`:** ComfyUI on the same PC, with optional Wan2GP (recommended for 16 GB cards and smaller, since it's more VRAM-efficient) and optional Stability Matrix as the model manager.
- **`dual_pc`:** ComfyUI and Forge on a generation PC, with polish and packaging on the main PC. Wan2GP and Stability Matrix packs are off.

### Rules that keep dead parts out (Owner's "no dead things")

- Every pack has a **health check** and a **smoke test**. A pack only ships as "supported" if its test passed for that release.
- A pack nobody maintains moves to an **archive tag** in git, then is removed from the build. It isn't left in place half-working.
- The README's program table and the agent's program list are **generated from the pack list**, so they can't disagree.
- Branches stop being "public vs private copies of everything." Layout and adult content become settings, so fewer things drift apart.

### Suggested pack status to start with (needs Owner check)

- **Keep, dual-PC:** `comfyui`, `forge`, `ollama`, `post`, `files`, `kokoro`
- **Keep, single-PC only:** `wan2gp`, `stability_matrix`
- **Decide (section 14):** `moss`, `blender`, the Rin storyboard example (built on Wan2GP), and the old `i2v_gpu` and Wan 2.1 legacy video paths

---

## 3. Compatible programs list

**Idea:** Owner. **Format:** Claude.

One file, `programs.yaml`, is the single source of truth. From it:

- the README gets a generated **"Works with"** table,
- One Desk shows it in Settings → Programs, with a live status dot,
- the agent reads it through a `list_compatible_programs` tool and in `get_generation_context.programs`, so it knows what the user has and what each program is for.

**Status levels:**

| Level | Meaning |
|---|---|
| **Tailored** | Built and tested for it every release. Best experience. |
| **Works with** | Tested, fewer tailored features. |
| **Single-PC option** | Supported only in the single-PC layout. |
| **Recommended (you run it)** | A program the user drives themselves. The agent can hand off to it but never automates it. |

**Draft list (Owner to confirm):**

| Program | Proposed level | Role |
|---|---|---|
| ComfyUI (any install) | Tailored | Generation backend |
| Forge | Tailored | Face and global refine |
| Ollama | Tailored | Local brains |
| Krita + Krita AI Diffusion plugin | Recommended (you run it) | Freehand painting, custom inpaint |
| Wan2GP | Single-PC option | VRAM-efficient hero video and lip sync |
| Stability Matrix | Single-PC option | Model manager and ComfyUI launcher |
| xAI Grok | Works with (optional cloud) | Cloud brain; images stay local |
| Kokoro | Works with | Book read-aloud and TTS |
| Cursor, Jan, LM Studio, Open Interpreter | Works with | MCP hosts other than One Desk |
| InvokeAI | Decide (section 14) | The owner uses it by hand; public status open |
| Blender | Decide (section 14) | Pose and depth maps |

Each entry also records the **tested version** and a link, so "works with" has a date on it.

---

## 4. Krita hand-off

**Idea:** Owner (Krita as the one user-run program, plus the conversational hand-off). **Research and design:** Claude.

### What the plugin allows (checked 2026-09-29)

- Krita's AI plugin is **Krita AI Diffusion** (by Acly). It talks to **ComfyUI** and can use a remote one, so Krita on the main PC can use ComfyUI on the generation PC.
- **Forge:** as far as I know, the plugin is ComfyUI-only, and the older Krita plugin for the Stable Diffusion WebUI family was archived. So Krita's built-in AI tools run through ComfyUI, and Forge stays agent-driven from One Desk. Owner should confirm there's no Forge route in use (section 14).
- The plugin stores **styles** as plain JSON files in `%APPDATA%\krita\ai_diffusion\styles\`. A style holds the checkpoint, LoRAs with strengths, style prompt, negative prompt, sampler, steps, CFG and VAE. An agent can write one of these files, so **"load these models for me" is possible without automating Krita.**
- Model files themselves live on the ComfyUI server, not in Krita. A recommended checkpoint or LoRA has to exist on that server before a style can use it.
- **Not found on this PC:** Krita wasn't in the usual install folders here and there's no plugin data in `%APPDATA%\krita`. It may be installed somewhere else.

### The conversation, step by step

1. **User:** "I'm going to edit this image myself in Krita."
2. **Agent:** opens the image in Krita, running `krita.exe <file>`. One Desk marks the image as "in Krita" in the filmstrip and starts watching the file.
3. **Agent reports what's loaded.** There are two sources:
   - **What the image was made with:** read from the image's own metadata (prompt, checkpoint, LoRAs, seed), or from the MCP's prompt log.
   - **What Krita is using right now:** read from the most recent Krita job in ComfyUI's history, which lists the checkpoint and LoRA nodes. This is reliable because every Krita job passes through ComfyUI. Before the first Krita job, report the style the user has selected, if it can be read.
4. **Conversation:** the user describes what they're doing ("I'm repainting her hand and want it to match the anime lineart"). The agent recommends a checkpoint, LoRAs and strengths. It uses the MCP catalog that already exists: food groups, `resolve_style_lane`, character LoRAs, and the Forge denoise guidance for touch-ups.
5. **"Load them":** the agent writes a style file named `One Desk - <name>.json` into Krita's styles folder, after first checking that each model exists on the ComfyUI server. It tells the user to pick that style in Krita's AI docker. If the plugin doesn't pick up new files live, the user clicks refresh; this still needs testing.
6. **Round trip:** when the user saves in Krita, the new version appears in the One Desk filmstrip. The old version stays as a revision, and the undo journal records it (section 7).

### Safety rules for the Krita pack

- The agent only ever writes files starting with `One Desk - `. It never edits or overwrites the user's own Krita styles.
- The Krita styles folder is outside One Desk's normal folders, so it has to be added explicitly in Settings (Batch 2 path limits apply).
- Krita jobs go straight to ComfyUI, so the MCP's GPU lock can't see them. While an image is "in Krita", One Desk warns before starting agent video or other heavy GPU jobs.
- Style recommendations follow the adult content setting (section 5). With it off, NSFW checkpoints and LoRAs are never suggested.
- Krita is GPL: link to it, never bundle it.

### Tools this needs (Claude)

| Tool | Does |
|---|---|
| `open_in_krita(path)` | Launch Krita with the image; mark it "in Krita" |
| `krita_status()` | Is Krita installed, is the plugin present, where is its styles folder, what did the last Krita job use |
| `recommend_krita_models(goal, image_path)` | Checkpoint, LoRAs, strengths and prompt from the catalog; no GPU |
| `write_krita_style(name, checkpoint, loras, ...)` | Write the `One Desk - ` style file after checking the models exist |
| `check_krita_readiness()` | Report which ComfyUI nodes and models the plugin needs that are missing. Report only; installs nothing without asking. |

---

## 5. Adult content (NSFW) setting

**Idea:** Owner (hidden unless toggled on). **Enforcement design:** Claude.

**Today:** One Desk has no adult-content handling at all. The MCP's NSFW tools, LoRA bundles and prompt rules are always loaded and always described to the agent.

**Proposal:**

- **Settings → Content → "Adult content", off by default.** Turning it on shows a one-time confirmation that the user is an adult and that this content is legal where they are.
- **The MCP enforces it too, not just One Desk.** Hiding it only in the UI wouldn't stop Cursor, Jan or another MCP host from using those tools. So `config.yaml` gets `content.adult: false` by default, and when it's off:
  - adult-only tools aren't registered (same tag system as the packs),
  - NSFW LoRA bundles, styles and catalog entries are hidden from listings and recommendations, including Krita recommendations,
  - the NSFW parts of the agent's instructions and prompt rules aren't sent.
- **One Desk follows the MCP.** When One Desk turns the setting on, it updates the MCP config; the MCP restarts to pick up the change.
- **Optional:** blur adult thumbnails in the filmstrip until clicked, for users who want the content available but not on screen.
- **This rig:** on.

---

## 6. README and "current setup" clean-up

**From:** Owner (need), Claude (specifics). This comes after the pack design, so the docs describe the new structure.

- **Root README:** replace the Stability Matrix requirement with "ComfyUI, any install." Describe the two layouts and link the generated programs table. Replace the hand-kept 17-tool table with tool groups plus a generated full list. Fix the broken Documentation table.
- **MCP README:** Stability Matrix becomes a single-PC note. Troubleshooting says "start ComfyUI (headless is fine)." Check whether workflow JSON still needs copying anywhere.
- **One Desk README:** replace "Get update runs `git pull`" with the manual update and rollback steps. Fix placeholder links. Use "Jobs" consistently. Add a short "Why One Desk exists" paragraph from the book-writing angle (Owner's story).
- **What agents are told:** the MCP's startup instructions, `AGENTS.md`, `onboarding/` and `.cursor/rules/stability-studio-*.mdc` should describe packs, layouts, the programs list and the adult setting. They should drop Stability Matrix as Tier 1 and the old 16 GB-only framing. The VRAM routing rule ("≥ 24 GB: never offer Wan2GP") should become "Wan2GP is a single-PC option, recommended for low VRAM."

---

## 7. One Desk UI

| Idea | From |
|---|---|
| **Undo for agent actions: an action journal.** Every change the agent makes is recorded with what it looked like before: accepted edits, recycled media, renames and moves, settings, backend switches, ships into `game/`, Krita round trips. A "Recent actions" panel has an Undo button per entry. Restores follow the Recycle Bin rule. Actions that can't be reversed (a finished render, a Grok request) are labelled that way. Undo refuses if the file changed since. | Claude (Owner asked for the detail) |
| **Confirm before bulk actions.** "The agent wants to recycle 12 images. Show list / Allow / Cancel." | Claude |
| **Settings → Programs** page: the compatible programs list with live status, pack on or off, layout choice. | Both |
| **"In Krita" badge** on filmstrip images that are open in Krita, with an "Open in Krita" button. | Both |
| **Side-by-side compare** of an original and an edit (slider or split view). | Claude |
| **Frame gate viewer for video.** Show the first, middle and last frames next to the source still, with Keep / Reject. | Claude |
| **Image metadata panel.** Show prompt, seed, model and LoRAs for any still, with a "Recreate" button. | Claude |
| **Model folders chosen by the user** in Settings, not fixed paths. | Both |
| **Command palette** (Ctrl+K) and a keyboard shortcut list. | Claude |
| **Split `app.js`** into modules (already under "Later" in the handoff). | Claude |
| **Resizable chat panel; the viewer grows to fill the space** (section 7.1). | Owner (idea), Claude (details) |

### 7.1 Resizable chat panel

**From:** Owner (let the user shrink and expand the chat, and have the viewer enlarge automatically). **Details:** Claude.

Today the chat and the right pane (Document / Image / Video) are a fixed 50/50 split (`.main { grid-template-columns: 1fr 1fr }` in `app.css`).

- **Divider bar** between chat and viewer. Dragging it resizes the chat, and the viewer takes all the remaining space; that's the automatic enlarge. The GPU monitor's existing `panel-resize` handles are the pattern to reuse.
- **Three quick sizes** as small buttons on the divider (double-clicking the divider cycles them):
  - **Wide chat** (about 60/40), for writing and planning,
  - **Balanced** (50/50), the default,
  - **Viewer focus:** the chat shrinks to a narrow strip that still shows the last message and the input box.
- **Collapse fully:** the chat folds into a thin bar on the left. A dot appears on it when the agent replies, and clicking it brings the chat back.
- **Remembered per mode** (agreed): Document, Image, Video and Editing each keep their own width, saved in Desk settings. One Desk suggests a starting size once (**Editing opens in Viewer focus**); after that the user's choice wins.
- **Limits:**
  - chat at least about 280 px unless collapsed, so the input box and buttons stay usable,
  - viewer at least about 360 px,
  - on small windows the quick sizes stack the panes instead.
- **The viewer's content follows the new size:**
  - images fit the new space,
  - the video player scales,
  - the Editing timeline gets wider, so more film shows at the same zoom.

  Real proportions are always kept (e.g. Rin's 480×704 portrait).
- **Keyboard:** the divider can take focus and arrow keys move it; **Ctrl+\\** toggles Viewer focus. It's listed in the shortcut list.
- **Order:** it's a small, separate change (CSS grid plus a little JavaScript and a setting), so it can land before Editing, which benefits from it most.

---

## 8. Release and updates

| Idea | From |
|---|---|
| **Manual update with rollback.** Each release ships as a versioned folder or installer. Settings, chats and themes live in the Desk folder, which updates never touch. "Roll back" means launching or reinstalling the previous version. | Owner (manual + rollback), Claude (mechanics) |
| **Settings migration safety.** Before a new version changes the `settings.json` format, it saves `settings.v<old>.json` so a rolled-back version still has a copy it can read. | Claude |
| **Third-party notices.** Python packages from `pip-licenses`; a hand-kept list of fonts, bundled workflows, ComfyUI node packs the MCP installs, and recommended programs (Krita). Never bundle model weights. | Both |
| **Version shown in the app** (Settings → About) and a "What changed" note per release. | Claude |
| **Diagnostics export.** One button zips recent logs and a settings summary with keys, tokens and paths redacted. Local only. | Claude |
| **Code signing** for the installer eventually, to avoid Windows SmartScreen warnings for new users. | Claude |

---

## 9. Writing (the book side)

| Idea | From |
|---|---|
| **Story bible:** character cards, places and timeline, linked to the manuscript, so the Writing job checks them before suggesting edits. | Claude |
| **Continuity check:** on request, flag contradictions against the story bible. Reports only; never auto-edits. | Claude |
| **Revision history viewer** for the snapshots `revisions.py` already takes on Accept. | Claude |
| **Outline or scene board:** chapters and scenes as reorderable cards linked to files. | Claude |
| **Word count goals** per session and per chapter. | Claude |
| **Export** to DOCX or EPUB through Pandoc, installed separately by the user (GPL; not bundled). | Claude |
| **Read-aloud proofing** with Kokoro. | Claude |

---

## 10. Prompt writing

| Idea | From |
|---|---|
| **Prompt linter.** Flag known traps before a render: "camera" words, house words like "gold standard" that the model would draw, vague toy wording, solo scenes missing solo negatives, invented fluids. Built from `.cursor/rules/nsfw-sex-prompting.mdc`; the adult checks only run with adult content on. | Both (your rules, my tool) |
| **Prompt library** with versions and a keep or reject rating per result. | Claude |
| **Negative prompt presets** per food group and scene type. | Claude |
| **A/B grid:** same seed, two prompts or two LoRA weights, side by side. | Claude |

---

## 11. MCP (other than packs)

| Idea | From |
|---|---|
| **Tool groups per job** inside the enabled packs (`stills`, `faces`, `video`, `post`, `audio`, `files`), so a small local model sees 15–25 tools, not 100. | Claude |
| **Generated tool list** for the README, built from the server itself. | Claude |
| **`doctor` command:** checks `config.yaml`, each enabled pack's health check, and missing models or nodes, in plain words. | Claude |
| **Dry run** for anything that changes files or costs GPU time. | Claude |
| **Consistent errors:** every tool returns `ok`, a short `error` and a `fix` hint. | Claude |
| **No hard-coded IPs or hostnames** in code; config only. | Claude |
| **MCP as a separate process** from One Desk (already under "Later"). | Claude |

---

## 12. Editing: basic video and audio editor

> **Scope note (Owner, 2026-09-29):** Full manual Editing UI is a **Phase 2** item and a **public teaser** (this section + mockup). **Phase 0–1** ship **AI-only** post tools already in the MCP — no Editing button required for first beta. See section 16 and `Product_roadmap.md`.

**Idea:** Owner. A DaVinci Resolve-inspired editor inside One Desk, but only the basics, and friendly for non-technical users. Drag and drop, automatic or by hand. Clear buttons for **Merge**, **Loop** and **Ping Pong** (forward, then backward). Video clips on top; sounds dragged in below and slid left or right to line up with the picture. Each audio line has **arrows** to nudge its timing, **volume up and down**, and **Normalize**.

**Flow and saving (Owner, second round):**

- One Desk gets its own **Editing** button. Pressing it asks: **Video editing** or **Audio editing**.
- Video and audio are **two separate editors**. You splice the video first, then move to audio.
- A **hard Save** button lets the user **name the new video clip**.
- A **warning** shows while the clip isn't saved.
- Moving to the audio editor with an unsaved clip **forces a save first**.
- After saving, One Desk **asks whether to bring the clip into the audio editor**, so nothing is lost.

**Working with the agent (Owner, third round):**

- **Only the guide has a preloaded clip**, to showcase editing. Normal editing starts empty.
- The agent **can already splice on its own** with its tools. The editor is for when the **user wants to do the work or make slight edits**.
- "**Bring the clip up and show me where you spliced it.**" The agent opens its clip in the editor as a **film strip** with the joins marked. The user can **cut** it and **move pieces to retime** a little.
- A simple **agent review of the splices** gives feedback.
- **Same for audio.** User: "Audio is bad." Agent: "Would you like me to bring the video clip with no audio into the editor and overlay the audio tracks for your adjustment?" The agent switches to the audio editor, puts the video on top, and lays out the audio tracks **where it had them**.
- The user adjusts **volume** (no EQ yet) and **timing**, and **reorders lines up and down to set which is most prominent**, e.g. character voice on top, traffic second, footsteps third, ambient fourth.

**Design and technical plan:** Claude.

**Mockup for proofing:** `C:\Users\Creel\.cursor\projects\d-studio-agent\canvases\one-desk-edit-tab-mockup.canvas.tsx`. It opens beside the chat in Cursor. It's clickable: start with the Editing button, drag clips and sounds, try the buttons and the save flow. The agent panel has three scripted messages ("Bring the clip up and show me where you spliced it", "Review the splices", "The audio is bad") that act out the agent side. It shows the layout and behavior only; no real video.

### 12.0 The flow, step by step

1. Press **Editing** in the One Desk bar.
2. A chooser shows two large options:
   - **Video editing:** "Put clips in order, merge them, loop them or ping pong them. Save the result as a new clip."
   - **Audio editing:** "Put a saved video on top, then drag in dialogue, effects and music and line them up."
3. **Video editing:** splice with Merge, Loop and Ping Pong. While there are unsaved changes, a **"Not saved"** badge and a warning line say: "This clip has not been saved yet. Press Save video to name it and keep it."
4. **Save video** opens a name box. It shows what the file will be called and saves a **new** clip in `Post Production/`, in the chosen format (12.13).
5. Press **Audio editing** (the switch at the top of the editor):
   - **Not saved:** a warning appears: "This video hasn't been saved yet. Save it before going to the audio editor, so you don't lose your edit." The choices are **Save and continue** (opens the name box) or **Keep editing video**. There is **no "continue without saving"** option.
   - **Saved:** One Desk asks: "Bring this video into the audio editor?" **Yes, bring it over** puts the saved clip on the top line. **No, open it empty** opens the audio editor with an empty top line; any saved video can be dragged there later.
6. **Audio editing:** the saved clip sits on the top line, locked (it was finished in the video editor). Drag sounds in underneath, line them up, adjust volume and normalize.
7. **Save video with sound** opens the same name box, suggesting `<clip name>_with_sound`, and writes a new MP4 with the mixed audio.
8. Going **back to Video editing** with unsaved sound work shows the same kind of warning and forced save.

### 12.0.1 Saving rules

| Rule | Why |
|---|---|
| Save always writes a **new named clip** (WebM, MP4 or both, 12.13). Nothing is overwritten. | Recycle-Bin-only spirit: no silent loss |
| If the name is already used, the box says so and asks for another name. Re-saving the clip you're working on (same name) is allowed and replaces only that clip, with the previous version recycled first. | Plain names, no accidental overwrite |
| Names can't contain `\ / : * ? " < > \|`. The box explains this instead of failing. | Windows file-name rules |
| **Forced save** before switching from video to audio, and from audio back to video. | Owner's rule: don't lose the edit |
| Leaving Editing entirely (another tab, or closing One Desk) with unsaved work also warns, with **Save**, **Keep editing** and **Leave (keep draft)**. | A draft of the timeline is autosaved for crash recovery, but it isn't a named clip until Save. |
| Saved clips appear in the media bin under **Your saved videos**, so they can be used in either editor. | Easy round trips |
| Every save is recorded in the undo journal (section 7). | Undo a save by recycling the new file |

### 12.1 What it is and isn't

| In (the basics) | Out (leave to DaVinci and friends) |
|---|---|
| One video line of clips, in order | Multiple video layers, picture-in-picture |
| Any number of audio lines under it | Audio effects, EQ, compressors |
| Drag, drop, slide, snap | Color grading, LUTs |
| Merge, Loop, Ping Pong | Keyframes, motion graphics, titles |
| Film strip view, cut at playhead, trim by one frame (phase 2) | Multi-camera editing |
| Reorder audio lines to set prominence; ducking (phase 3) | EQ, reverb (maybe later) |
| Nudge, volume, Normalize, Mute per audio line | Speed ramps |
| Simple fade between clips (phase 3, one checkbox) | Transition library |
| Save one named clip: WebM (Ren'Py), MP4, or both | Render queues, codec settings pages |

### 12.2 Layout (top to bottom, as in the mockup)

**Both editors share:**

1. **Editor bar:** the **Video editing / Audio editing** switch, what's being worked on ("Working on rin_scene_01.mp4"), the **Not saved** badge, and the **Save** button (**Save video** or **Save video with sound**).
2. **Unsaved warning line** under the bar whenever there are unsaved changes.
3. **Media bin** on the left: clips from the project's `clips/` folder, sounds from `audio/`, and **Your saved videos**. Files can also be dragged in from Windows Explorer or the filmstrip. The video editor shows clips; the audio editor shows sounds plus saved videos.
4. **Preview** on the right: the frame under the playhead, with Start, Back 1 frame, Play and Forward 1 frame. In the audio editor, a line under it says which sounds are playing at that moment.
5. **Status line:** one plain sentence saying what just happened ("Rin bow now plays 2 times. Clips after it moved right to make room.").
6. **Timeline** with a time ruler in seconds (click it to move the playhead).

**Video editor toolbar and timeline:**

- Toolbar: **Merge clips**, **Loop**, **Ping Pong** (big buttons first), then **Auto-arrange**, **Remove from timeline**, **Undo** and the **Snap clips together** switch.
- Timeline: one **video line** of clips.

**Audio editor toolbar and timeline:**

- Toolbar: **Normalize all audio**, **Remove from timeline**, **Undo**.
- Timeline:
  - the **saved clip**, locked, on the top line,
  - one row per **audio line**, with its controls on the left: `-` / `+` volume with a dB readout, **Normalize**, **Mute**,
  - an empty **"Drop a sound here"** row that starts a new audio line.

### 12.3 How it behaves

**Video line**

- Drag a clip from the bin onto the video line. With **Snap clips together** on (the default), it joins the others with no gap. With it off, it lands where you dropped it, and clips only move to avoid overlapping.
- Drag clips left and right to reorder them.
- **Merge clips:** joins the selected clips (Shift+click to pick several) or, if none are selected, all of them, into one clip in timeline order.
- **Loop:** repeats the selected clip. Each press adds one more repeat. Clips after it move right.
- **Ping Pong:** makes the selected clip play forward, then backward. This matches the existing MCP `splice_pingpong` tool.
- **Auto-arrange:** closes all gaps.
- **Remove from timeline:** takes it off the timeline. The file on disk is never touched.

**Audio lines**

- Drag a sound onto the empty row to create a new line, or onto an existing line.
- Slide it left and right with the mouse. It **snaps** to the clip's start and end (and, later, to the joins inside a merged clip) within 0.15 seconds, and a guide line shows where it snapped.
- **Arrows on both ends of each sound** fine-tune its timing: the left arrow moves it 0.25 s earlier, the right arrow 0.25 s later (exactly 4 frames at 16 fps). Shift+click moves one frame for lip sync. See 12.12.
- `-` and `+` change volume in 1 dB steps, from −24 to +12 dB. The waveform grows and shrinks so the change is visible.
- **Normalize** sets that line to a standard loudness. **Normalize all audio** does every line, so dialogue, effects and music start from the same level.
- **Mute** silences a line without removing it.

**Everywhere**

- **Undo** reverses the last timeline change, back 20 steps or more. It ties into the action journal (section 7).
- A draft of the timeline is kept automatically for crash recovery. A **named clip only exists after Save** (12.0.1).
- Plain words on every button, and a tooltip on every small control.

### 12.4 Automatic and by hand

**By hand:** everything above works with the mouse alone.

**Automatic (agent-assisted):** the agent can do the same actions through tools, and the user sees them happen on the timeline and can undo them. Examples:

- "Put these three Rin clips in order and ping pong the bow." The agent places the clips and applies Ping Pong.
- "Line up the 'Well met' line with the start of the bow." The agent snaps the sound to that clip's start.
- "Put footsteps under the walk and make the music quieter than the dialogue." The agent places footsteps and sets music about 12 dB under the dialogue after normalizing.
- **Auto-align dialogue** (later): the agent finds where speech starts in a sound file (silence detection) and lines that point up with the chosen clip, instead of the file's first sample.

The agent never saves or overwrites anything without being asked, and it follows the same forced-save rule before switching editors: it asks the user for a clip name rather than inventing one.

### 12.5 Under the hood

- **Non-destructive edit list.** A timeline is a small JSON file in the project (`edits/<name>.timeline.json`): the clips, their start times, treatments (loop count, ping pong, merge group), and the audio lines with offsets, gain, normalize and mute. Source clips and sounds are never modified.
- **Save renders with ffmpeg on the main PC**, which fits the labor split: generation on ComfyBox, editing and packaging locally. A progress bar shows during the render; the clip is written under a temporary name and only renamed to the chosen name when it's complete, so a crash never leaves a half-written clip with the real name.
  - **Merge:** concatenate, reusing the MCP's `concat_video_clips` logic. When clips differ in size or frame rate, they're converted to the project's size and rate first. The current lossless join only works when they already match.
  - **Loop:** repeat the clip n times. **Ping Pong:** forward plus reversed, as `splice_pingpong` already does.
  - **Audio:** each line is delayed to its start time, gain applied, then all lines mixed down. This uses ffmpeg's `adelay`, `volume` and `amix` filters.
  - **Normalize:** ffmpeg's two-pass loudness normalization (`loudnorm`), measured once and cached per file. Suggested defaults: about −16 LUFS for dialogue-led projects, with a peak ceiling of −1.5 dB so nothing clips.
- **Preview** plays in the One Desk window (WebView2 video plus Web Audio for the audio lines), so no render is needed to check timing. For long timelines, a small low-resolution preview copy is made in the background.
- **Where the code lives:** the edit list, preview and UI in One Desk. The ffmpeg render and loudness measurement in the MCP `post` pack (section 2), so Cursor and other MCP hosts can use them too.
- **Clip sound:** Wan clips have no sound. For clips that do, their own sound shows as a linked audio line that can be muted or unlinked.

### 12.6 New MCP tools (for the automatic side)

| Tool | Does |
|---|---|
| `timeline_create(name)` | New empty timeline in the project |
| `timeline_add_clip(timeline, path, at=None)` | Add a clip (end of line by default) |
| `timeline_treat_clip(timeline, clip_id, treatment)` | `loop` (with count), `pingpong`, or `none` |
| `timeline_merge(timeline, clip_ids=None)` | Merge selected clips, or all |
| `timeline_add_audio(timeline, path, at=None, align_to=None)` | Add a sound; `align_to` = a clip id (start or end) |
| `timeline_adjust_audio(timeline, line_id, offset=None, gain_db=None, mute=None)` | Nudge, volume, mute |
| `normalize_audio(paths or line_ids)` | Measure and set standard loudness |
| `timeline_describe(timeline)` | Plain-language summary for the agent: what's where |
| `timeline_open_clip(clip_path)` | Open a clip in the video editor from its recipe, with join markers; falls back to guessed joins (12.10) |
| `review_splices(timeline)` | Check the frames either side of each join; return notes and suggested fixes; changes nothing |
| `timeline_open_audio_layout(clip_path)` | Open the clip's silent video in the audio editor with the recipe's audio lines, in their order, offsets and levels |
| `review_audio(timeline)` | Flag clipping, a voice buried under other lines, silence gaps; changes nothing |
| `timeline_combine_audio` / `timeline_split_audio` | Combine chosen audio lines into one mix, and undo that (section 12.14) |
| `timeline_save(timeline, name, format)` | Render one named clip (`webm`, `mp4` or `both`) into `Post Production/`; refuses a name that's already used |
| `timeline_port_to_audio(saved_clip)` | Open the audio editor with a saved clip on the top line; refuses if the video isn't saved |

### 12.7 Rules it follows

- **Recycle Bin only.** Removing from the timeline never deletes files. Recycling a file from the bin uses the normal recycle path and is recorded in the undo journal.
- **Adult content setting** (section 5): with it off, the media bin hides clips marked as adult, and the agent won't place them.
- **No GPU:** editing and saving are ffmpeg only and never touch ComfyBox.
- **Third-party notices** (section 8): ffmpeg's license depends on the build (LGPL or GPL). Either use the ffmpeg build that `imageio-ffmpeg` already installs, or have the user install ffmpeg, and list it in the notices.

### 12.8 Phases

| Phase | Delivers |
|---|---|
| 0 | **Recipes.** The MCP splice and audio-mix tools write a `.recipe.json` next to every clip they make (12.10). This comes first, because "show me where you spliced it" depends on it, and every clip made before recipes exist can't be reopened properly. |
| 1 | Editing button and Video / Audio chooser; video editor with media bin, drag, snap, Merge, Loop, Ping Pong, Remove, Undo; **Save video** with name box and the unsaved warning; guide sample |
| 2 | Film strip view, **Cut at playhead**, trim by one frame, join markers; agent "show me where you spliced it" (opens a clip from its recipe) |
| 3 | Audio editor: forced save and "bring this video over?" prompt, locked clip on top, audio lines with drop, slide, snap, nudge, volume, Mute, Normalize, **Up / Down reorder**, **Auto-balance by order**, **ducking**; agent "audio is bad" layout; **Save video with sound**; reopen finished clips ("Original sound" line when there's no recipe); **Combine / Split** (12.14) |
| 4 | Preview playback with sound; one-checkbox fade between clips; **agent splice review** and audio review; "auto-align dialogue" |

Phases 0–3 give a usable editor that works with the agent. Phase 4 makes it comfortable and adds the reviews.

### 12.9 Questions for Owner on the editor

- ~~Frame rate~~ **Proposed (Claude, 12.13):** keep the project's frame rate (16 fps for Wan) by default. Ren'Py drops frames when movies on screen together have different frame rates, so a game should use one rate throughout. Converting a whole project to 24 or 30 fps stays an option.
- ~~Where it lives~~ **Answered (Owner):** its own **Editing** button with a Video / Audio chooser.
- **Existing Video pane:** keep it for Wan generation only, with a "Send to Editing" button on finished clips? (Claude's suggestion.)
- **Fades:** is a single "fade between clips" checkbox wanted in phase 3, or no transitions at all?
- **Loudness target:** −16 LUFS (web and video standard) as the default, or something else for your game and VN work?
- ~~Ducking amount~~ **Answered (Owner):** start at the minimum recommended amount, **6 dB** (the low end of the usual 6–12 dB range for keeping speech clear over other sound), with a quarter-second fade and an on/off switch. It can be raised later if voices still get buried.
- ~~Guide sample~~ **Answered (Owner):** use the **original Rin** example in `onboarding/examples/rin/`. It was made with this MCP.

### 12.10 Working with the agent

**From:** Owner (the conversations and the goals), Claude (how to make them work).

#### Guide only has a preloaded clip

- Normal Editing opens **empty**, with a hint: "Drag clips here from the Media bin, or ask the agent to bring one up."
- **Open the guide** (on the chooser) loads a practice sample and marks the editor **Guide sample**. The guide's clip is never saved over the sample; its Save suggests `guide_practice`.
- The sample ships with onboarding (Tier 0, no GPU needed), so a new user can learn the editor before generating anything.

**Guide sample: original Rin (Owner).** What's in `onboarding/examples/rin/` today (checked 2026-09-29):

| File | What it is |
|---|---|
| `clips/Rin_clip1_walk_hero.mp4` | Walk, 49 frames at 16 fps (3.06 s), 480×704 portrait, no sound |
| `clips/Rin_clip2_bow_petals.mp4` | Bow with petals, 49 frames (3.06 s), no sound |
| `final/Rin_storyboard_spliced.mp4` | The finished splice, 118 frames (7.38 s), **no sound track** |
| `images/Rin_kitsune_approved.png`, `images/Kitsune_blossom_hero.png` | Source stills |

**Gaps to fill before it works as a guide:**

- **No sound files.** The README says the scene has MOSS dialogue and SFX, but the finished splice has no audio stream and no sound files exist anywhere in the repo. The audio half of the guide needs Rin's three lines ("Greetings." / "My name is Rin, you killed my father." / "Now prepare to die.") and a couple of effects. They could come from Kokoro (CPU, no GPU needed) or from MOSS on ComfyBox. **ComfyBox generation only when you say so.**
- **No separate lunge clip.** The final is 118 frames, but the two clips are 49 each, so about 21 frames of lunge exist only inside the final. Either add the lunge clip or have the guide use walk and bow, with the final as the "agent-made" example.
- **No recipe yet.** The exact join points in the final aren't recorded. A recipe for it would be written by hand once (or rebuilt when the splice is redone with recipe-aware tools), so "show me where you spliced it" works on the guide.
- **README fix** (goes with the README clean-up, section 6): it says "with MOSS dialogue and SFX" and describes three beats, but the files have no sound and two clips.
- **Portrait video:** Rin is 480×704. The editor preview should fit portrait and landscape clips, not assume 16:9.

#### Recipes: the part everything else depends on

For "show me where you spliced it" and "lay the tracks out where you had them" to work, the agent has to **remember how it built the clip**. Today the MCP splice tools (`concat_video_clips`, `splice_pingpong`, the loop tools) and the audio tools just write an MP4.

**Proposal:** every clip the agent or the editor makes gets a small **recipe file** beside it (`rin_bow_sequence.recipe.json`), listing:

- the source clips, each piece's in and out points, and its treatment (loop count, ping pong),
- where each join falls,
- the audio lines: source file, start time, gain, normalize, mute, and **order**,
- which tool or person made it, and when.

Then:

- **With a recipe**, the editor rebuilds the exact timeline: pieces, joins, audio lines in their places.
- **Without a recipe** (clips made before this exists, or from elsewhere):
  - **Video:** the agent can still **guess** the joins with ffmpeg scene-change detection. It marks them "guessed joins" so the user knows they may be off.
  - **Audio:** a finished mix **can't be pulled back apart** into separate voice, traffic and footsteps. The agent must say so honestly and offer the mixed sound as one line, or rebuild the mix from the source sounds if it still has them.

#### "Show me where you spliced it": film strip, cut and retime

- The agent calls `timeline_open_clip`. One Desk switches to **Video editing** with **Film strip view** on: each piece shows a row of frame thumbnails, the ruler labels **Join 1**, **Join 2**, and a thin line runs through every lane at each join.
- The agent's message says where the joins are in words ("walk, bow, lunge; joins at 3.00s and 6.10s").
- **Cut at playhead** splits a piece in two. Either half can then be dragged, trimmed or removed.
- **Trim 1 frame from start / end** removes single frames (Wan is 16 fps, so one frame is 1/16 s).
- Dragging a piece moves it in **whole frames**. With **Snap clips together** on, the pieces after it close up; with it off, you can leave a gap.
- Opening the agent's clip doesn't mark it unsaved. The first change does, and Save then suggests a new name so the agent's original stays intact.

#### Agent splice review (simple feedback)

- "Review the splices" makes the agent look at the **last frames before and the first frames after each join**. It uses the frame-viewing and gate tools it already has, plus the pose matching in `splice_pose_matched_loop`.
- It adds an **Agent review** row under the video line with a note at each join: **OK** ("Clean join. Pose and lighting match.") or **Needs work** ("Pose jumps: her arm snaps up. Trim 2 frames from the start of the next piece.").
- A note that needs work has an **Apply** button that makes exactly the suggested change, as one undoable step. The agent **never applies fixes on its own**; notes are advice.
- Any change to the timeline clears the old notes, since they no longer match.
- **Typical fixes:** trim a few frames either side of the join, move the join to a better-matching frame nearby, or (phase 4) a short 2–4 frame fade.

#### "The audio is bad": agent lays out its tracks

1. The user says the audio is bad. The agent offers: "Would you like me to bring the clip into the audio editor with no audio, and lay the sound tracks out where I had them?"
2. **Yes:**
   - If the video editor has unsaved changes, the agent triggers the same **forced save** first. It never skips it.
   - Then `timeline_open_audio_layout` switches to **Audio editing**. The clip goes on the top line with its **sound removed** ("rin_bow_sequence.mp4 (sound removed)"), and the recipe's audio lines are laid out underneath, in the agent's order, times and levels.
3. The agent can add a hint ("the footsteps are too loud in my mix") or run `review_audio` and mark problems.
4. The user adjusts, then **Save video with sound** writes a new clip. The agent's original is untouched.

#### Line order sets prominence: my thoughts

Your idea (voice on top, traffic second, footsteps third, ambient fourth) is the easiest way for a non-technical person to say "what matters most." One catch: in normal editors, **line order alone doesn't change the sound**; the order is only visual. To make reordering actually do what the user expects, I'd tie it to two things:

- **Auto-balance by order** (one button): normalizes every line, then sets levels by rank. Line 1 at 0 dB, line 2 at −6, line 3 at −10, line 4 at −14, and lower from there. The user can still fine-tune each line with `-` and `+` afterwards.
- **Ducking** (a switch, on by default): while a higher line is playing, the lines below it dip automatically, by **6 dB** (Owner: start at the minimum recommended amount) with a short fade, then come back. When Rin speaks, the traffic and footsteps dip under her voice without anyone drawing volume curves. The waveform in the mockup shrinks on ducked lines to show this.

Together they make **Up** and **Down** meaningful: move footsteps above traffic and they become clearer, both in level and because traffic now dips under them.

The rest of each audio line stays as planned: end arrows (0.25 s, Shift = one frame, section 12.12), `-` `+` volume, Normalize, Mute. No EQ yet, as you said.

#### The agent inside the editor

The agent panel sits beside the preview in both editors. The same conversation continues when switching between video and audio. Everything the agent does in the editor is visible, undoable and follows the save rules; it can't save or overwrite without the user.

---

### 12.11 Timeline look: grey background, blue time grid, film on top

**From:** Owner (grey background, blue lines, film on top, each line a unit of time or frame; frame numbers; grid colour both automatic and user choice). **Details:** Claude.

- **Background:** grey lanes. **Grid:** blue vertical lines running down through **every** lane (ruler, film, review notes, all audio lines), so lining a sound up with a frame can be done by eye.
- **Two line weights:**
  - **Second lines:** stronger, labelled in the ruler.
  - **Frame lines:** fainter, one per frame. They only appear when zoomed in far enough that a frame is at least **8 pixels wide**, so zoomed out they don't blur into a haze. A **Zoom** slider sits above the timeline.
- **The grid matches the snapping.** Clips and sounds move in whole frames, so what the grid shows is where things land.
- **Frame numbers:** the ruler can show `sec:frame` (e.g. `3:01` = 3 seconds, frame 1), with small frame numbers between seconds when zoomed in. A switch goes back to plain seconds. Agent notes use the same format ("trim 2 frames at 6:01").
- **Film on top:** the video line is drawn as film: neutral grey pieces with sprocket-hole bands along the top and bottom and one thumbnail cell per frame. Audio lines stay green below it.
- **Colours kept apart so nothing blends into the blue grid:**
  - **Playhead:** high-contrast white (black in light themes).
  - **Join markers:** amber, labelled Join 1, Join 2.
  - **Video pieces:** neutral film grey, not blue.
  - **Selection:** the theme's accent outline.
- **Grid colour: automatic and user choice (Owner: "both is better").**
  - **Auto** (default): grey and blue taken from the One Desk theme, with the line strength adjusted so it stays visible in light and dark themes.
  - **User choice** in Settings → Editing: grid colour, line strength and playhead colour, plus **Back to automatic**. The mockup shows the choice as Auto / Blue / Cyan / Purple.
- **Portrait and landscape:** the preview fits the clip's real shape (Rin is 480×704 portrait), not a fixed 16:9 box.

### 12.12 Audio fine-tuning and preview

**From:** Owner (arrows on each side of the audio, 0.25 s steps, snap for first placement and arrows for fine-tuning, play both together before saving). **Details:** Claude.

- **Snap = first placement.** Dragging or dropping a sound snaps it to the clip's start, end or joins (within 0.15 s), and a guide line shows the snap.
- **Arrows = fine-tune.** Each sound block has an arrow on **each end**:
  - left arrow: **0.25 s earlier**,
  - right arrow: **0.25 s later**,
  - 0.25 s is exactly **4 frames** at 16 fps, so every click lands on a frame line,
  - **Shift+click:** one frame, for lip sync,
  - the arrows **ignore snapping**, so a sound can be moved off a snap point on purpose,
  - each click is its own Undo step, and the status line says the new start time.
- **Preview before saving: "Play video + sound".**
  - Plays the video and all audio lines together from the playhead, with the current volumes, mutes, normalize and 6 dB ducking applied.
  - The preview uses the **same numbers Save uses**, so what you hear is what gets saved. Normalize is measured once per file and the same volume change is applied in both.
  - **Loop a section:** mark a short stretch (e.g. the 2 seconds around a line) and play it on repeat while nudging.
  - **After saving**, the finished file opens once in a player for a final check before the user calls it done.
  - **How:** the WebView2 video element is the clock; Web Audio plays each line through its own volume control and applies the ducking in real time. Long timelines get a quick low-resolution preview copy in the background.

### 12.13 File formats (MP4 and WebM for Ren'Py)

**From:** Owner (a choice between MP4 and the web format Ren'Py likes). **Research and details:** Claude. Checked against the Ren'Py movie documentation, 2026-09-29.

**What Ren'Py plays:**

- **Desktop Ren'Py can't decode H.264 or AAC**, which is what nearly every MP4 uses. An ordinary MP4 won't play in a desktop Ren'Py game; it only works in Ren'Py **web** builds, where the browser plays it.
- Ren'Py plays AV1, VP9, VP8 and Theora video, with Opus or Vorbis audio, in WebM, Matroska or Ogg. For commercial games it **recommends** those formats, since others may need patent licences.

**The Save box offers:**

| Choice | Makes | For |
|---|---|---|
| **WebM (Ren'Py)** | VP9 video + Opus audio | Ren'Py desktop games (recommended) |
| **MP4** | H.264 video + AAC audio | Sharing, social media, normal players, Ren'Py web builds |
| **Both** | One of each, same name | Games that also have a web build (Safari needs MP4) |

**Details:**

- **Default:** WebM is pre-selected when the project has a Ren'Py game folder; MP4 otherwise.
- **Quality:** a simple **Good / Best** choice, not codec settings. VP9 takes noticeably longer to encode than H.264, so the progress bar matters.
- **Frame rate:** keep the project's rate (16 fps for Wan). Ren'Py warns that movies shown on screen together must share a frame rate or it drops frames, so a game should use one rate throughout.
- **Loops:** Ren'Py's Movie displayable loops by itself. An idle loop can be saved as one ping pong and left for Ren'Py to repeat, instead of baking in many repeats.
- **Voice lines (option):** baking voice into the video means players can't control voice volume separately, which Ren'Py normally allows. A setting "Also save audio lines as separate files (Opus)" lets voice go through Ren'Py's voice system.
- **File names:** with WebM chosen, the name box suggests a game-safe name (lowercase, no spaces) with a one-click **Use `<safe_name>`** button.
- **Where it saves:** `Post Production/` (section 13), never straight into `game/`. **Send to game** is a separate, approved step from Keepers.
- **Later, not now:** transparent movie sprites. Ren'Py can't play video with transparency directly, but it supports a side-by-side mask; that could become a "transparent background" option.
- **Third-party notices:** the ffmpeg build used must include VP9 (libvpx) and Opus encoders; list it in the notices (section 8).

### 12.14 Reopening finished clips, more audio lines, Combine and Split

**From:** Owner (take a finished product back in and add audio; more than 4 lines; combine the lower background sounds, then work on dialogue). **Details:** Claude.

**Reopening a finished clip to add more audio**

- **Saved from One Desk (has a recipe):** opening it rebuilds the timeline with every sound still on its own line. The user adds lines or moves things, then saves under a new name. The earlier save is untouched.
- **Made elsewhere (no recipe):** its sound can't be split back into parts. It comes in as one locked line, **"Original sound"**, which can be turned down, muted or ducked. New lines (e.g. dialogue) go on top of it.
- **Open for audio** shows on any video in the media bin and on the filmstrip; `timeline_open_audio_layout` handles both cases.

**No line limit**

- There's no cap on audio lines; the "Drop a sound here" row always adds another.
- **Auto-balance** keeps stepping down past line 4: −14, then −17, then −20 dB, with a floor at **−24 dB** so nothing becomes inaudible.
- Past about 6 lines, lines can switch to a **compact height**, and the audio area scrolls while the video line stays pinned at the top.

**Combine and Split**

- **Combine:** the user selects two or more lines (e.g. traffic, footsteps, ambient) and clicks Combine.
  - One Desk mixes them, with their current timing, volume, normalize and mute, into one new file in `Audio/` (e.g. `bg_mix_01.opus`). The file is never overwritten.
  - The selected lines are replaced by one line, **"BG mix (3)"**, placed where the highest of them was.
  - The original lines are kept inside the recipe, not thrown away.
- **Split** brings the original lines back exactly as they were, in their order and at their levels. The mix file stays in `Audio/`, so the user can recycle it by hand if they want.
- **A combined line** has its own timing arrows, volume, Normalize and Mute, which act on the whole mix. To change one sound inside it, the user splits it first.
- **Ducking:** a combined background counts as one line, so it dips as one under dialogue, which sounds more even than three separate dips.
- **Ren'Py export:** with "Also save audio lines as separate files" on (12.13), a combined mix exports as one background file and dialogue stays separate, which is usually what a game wants.
- **The agent can offer it:** "I combined your three background sounds so you can focus on the dialogue. Say 'split' to get them back." It uses the new tools below and never combines without saying so.
- **Undo** reverses a Combine or a Split like any other step.

**New MCP tools**

| Tool | Does |
|---|---|
| `timeline_combine_audio(timeline, line_ids, name=None)` | Mix the chosen lines into one file in `Audio/` and replace them with one combined line; the originals stay in the recipe |
| `timeline_split_audio(timeline, line_id)` | Restore a combined line's original lines |

---

## 13. Project folders: fresh-start default for end users

**From:** Owner (the layout, and the flow it's based on). **Details:** Claude.

This is the **default for a new user starting fresh**, shaped by the owner's own experience of making a book and a game. Users who already have their own project folders can map them instead (below).

### 13.1 The flow it supports

1. New images and clips land in a working folder.
2. The user refines, hand-inpaints (e.g. in Krita) or edits, and the good ones go into a **Keepers** folder.
3. When the project is finished, the loose files go into an **Originals** folder and get archived.
4. **Keepers** are added to the game.

### 13.2 Default layout

```text
My Project/
  Images/              new stills, refines, hand inpaints
    Keepers/
  Video/               new clips
    Keepers/
  Audio/               voices, effects, music
    Keepers/
  Assets/              source stills, character refs, fonts, licensed music
  Post Production/     Editing timelines, recipes, saved edits
    Keepers/
  Originals/           filled only by Finish project
  .onedesk/            hidden: temporary render files, logs
```

### 13.3 How it works

- **Keep button.** On the filmstrip and in the Editing media bin, **Keep** moves a file into that type's `Keepers/`. It moves rather than copies, so there's only ever one copy of each file. Dragging in Explorer works too.
- **Rejects go to the Recycle Bin, not a folder.** The current project template has a `rejected/` folder; it's dropped, to match the Recycle-Bin-only rule and the MCP's own "fails go to Recycle Bin" policy.
- **Editing reads the layout.** The video editor's media bin lists `Video/Keepers` first, then the rest of `Video/`; the audio editor does the same with `Audio/`. Saved edits and their recipes go to `Post Production/`; approved edits go to `Post Production/Keepers/`.
- **Optional character folders** inside each `Keepers/` (e.g. `Video/Keepers/Rin/`), matching the MCP's existing `Video/<Character>/` habit.
- **Finish project** (one button). It first shows exactly what will happen:
  - every non-keeper file moves into `Originals/`, keeping its subfolder (`Originals/Images/…`),
  - `Originals/` is zipped to an archive location the user chooses,
  - keepers and recipes stay where they are, so edits can still be reopened,
  - **nothing is deleted.**
- **Send to game** only from `Keepers/`. It follows the One Desk ship gate (Batch 3) and needs the user's approval. A small map in project settings says where each type goes, e.g. images to `game/images`, video to `game/movies`, audio to `game/audio` (optionally `voice/`, `sfx/`, `music/`).
- **Hidden clutter.** Temporary render files and logs go in `.onedesk/` inside the project, so users only see folders they're meant to touch.

### 13.4 Users with their own folders

Project settings list each **role** with a folder picker:

- new images, image keepers,
- new video, video keepers,
- new audio, audio keepers,
- assets, post production, originals,
- archive location, game folder.

One Desk and the agent work through those roles and **never rename or rearrange** the user's folders. The default layout is only the preset.

### 13.5 The MCP follows the same layout

The MCP's current project layout (`outputs.delivery`) and `onboarding/PROJECT.template` use different names. They'd map to the new ones, and old project config keeps working through the mapping:

| Now | Becomes |
|---|---|
| `images/` | `Images/` |
| `clips/` | `Video/` |
| `audio/` | `Audio/` |
| `assets/`, `source/` | `Assets/` |
| `final/` | `Post Production/` |
| `temp/`, `logs/` | hidden `.onedesk/` |
| `images/chain/` | `Images/` (chain frames), or `.onedesk/` if they're only intermediate |
| `rejected/` | removed (Recycle Bin) |

This touches `PATHS.md`, `onboarding/PROJECT.template`, the MCP's delivery config and `list_media_paths`, and the Rin example's folder layout. It belongs with the README clean-up (section 6).

---

## 14. Open questions for Owner

1. **Branches.** Once layout and adult content are settings, do we still need separate public and private branches, or one branch with a private `config.yaml`? And what is `dedicated-generation-server` for: keep, retire with a tag, or check first?
2. **Krita and Forge.** Is there a Krita-to-Forge connection you use today, or is "Krita AI through ComfyUI; Forge through the agent" right?
3. **Krita on this PC.** Where is Krita installed, and is the AI Diffusion plugin set up yet? It isn't in the usual folders.
4. **Krita style writing.** Write the `One Desk - ` style file automatically when you say "load them," or show it and ask first each time?
5. **InvokeAI.** Public "works with" entry, or private-only since you use it by hand?
6. **Undecided packs.** Keep, single-PC only, or archive: MOSS, Blender, ~~the Rin storyboard example~~ (**answered 2026-09-29: keep Rin as teaser/guide**), and the legacy `i2v_gpu` / Wan 2.1 video paths.
7. **Wan2GP on single-PC.** On by default for 16 GB cards and smaller, or always opt-in?
8. **Adult content.** Is the MCP-side enforcement (section 5) what you want, or One Desk-only hiding? Do you want the thumbnail blur option?
9. **Grok.** In the public build as an optional cloud brain, or private only?

---

## 15. Older suggested order (Claude, pre–Owner roadmap cut)

*Superseded for sequencing by **section 16** and `Product_roadmap.md`. Kept for history.*

1. Program packs (section 2)
2. Adult content setting (section 5)
3. README / programs table (sections 6, 3)
4. Krita pack (section 4)
5. Notices, version, manual update + rollback
6. Undo journal
7. Project folders (section 13) + resizable chat (section 7.1); then Editing §12
8. Tool groups / `doctor`
9. Writing bible + prompt linter

---

## 16. Agreed big-picture roadmap (Owner + Build AI, 2026-09-29)

**Canonical schedule:** `Product_roadmap.md`. This section is the conversation that produced it.

### 16.1 Editing is a teaser, not beta scope

Owner: first release will **not** ship user/manual video–audio editing. Phase 1 keeps **AI-driven tools already in the MCP** (concat, ping pong, mix, frame grab, etc.). Section 12 + the Cursor mockup (`one-desk-edit-tab-mockup.canvas.tsx`) stay as:

- a place the idea was hashed out while it was hot,
- a **public teaser** of what comes next,
- a way to gather excited feedback without support burden for an unfinished UI.

Build AI: approve; don’t let the mockup pull eng into timeline DnD before beta is reliable. Encoding **progress bar** when long ffmpeg saves exist.

### 16.2 Priorities

| Higher | Lower / later |
|---|---|
| Stable UI, workflows, locate/move media, guided setup | Manual Editing tab |
| Resizable / collapsing chat (enlarge viewer) | Ren'Py / WebM as default story |
| AI art + MCP + One Desk | Full draw suite / Invoke-level inpaint |
| Small batches, proof each | One mega upgrade |

### 16.3 Phase map (Owner wording)

**Phase 0 — Pre-release (current target era)**  
Initial product, tools, and workflows: AI-guided writing, prompting, storyboarding, image/video gen on local PC. Most users will not go beyond this. Recommended checkpoints and LoRAs for style (pose control optional). Recommended local AI models by task. Stable UI without crashes. Soft hardware guidance.

**Phase 1 — First beta package**  
Stable UI + workflows + full guided tour. Neat package: **One Desk** in the UI box, **MCP** in the MCP box (both required). Leave ComfyUI, Forge, Wan 2.2, Krita to the user; Comfy vs Stability Matrix with soft guidance from PC/RAM/GPU/VRAM. Headless Comfy + One Desk = AI-driven; Krita = human-driven. Agent manages workflows, checkpoints, LoRAs, prompt write/paste. **AI-only** post tools available; **no** manual Editing pane yet.

**Phase 2 — Depth**  
Blender (MCP early OK; One Desk UI when ready). **Manual** video + audio editor panes and AI-assisted editing UI (section 12). Full Kokoro toolset. PTT voice chat, STT for narration/notes, audio recording for VO/SFX.

**Phase 3 — Control polish**  
Minor face highlighting / region tools so Forge hits the right area. Light inpaint — not Krita/Invoke level unless demand or solid free code appears. Not a full draw suite unless the product is funding it.

### 16.4 Build AI notes that stuck

- Phase 0/1 success = **reliability + media locate/move + guided setup**, not feature count.
- Bundle Phase 1 AI post tools as a thin **post** job/tool group; hold the **Editing** button for Phase 2.
- Rebuild Rin guide as **bow + breeze + footsteps + JP hello** — don’t block on the lost full splice (exists on X).
- Collapsing/resizable chat lands in Phase 0/1 UI polish, before editors.
- Claude leads Editing product/UI contracts when Phase 2 starts; Build AI owns Desk wiring + MCP render tools; lock files in handoff.

### 16.5 Who builds what (when we get there)

| Slice | Lead |
|---|---|
| Editing UI (Phase 2) | Claude (design/mockup) + Build AI (Desk/WebView2) |
| Recipes + ffmpeg timeline tools | Build AI / MCP |
| Packs, NSFW, programs list, README | Claude |
| Krita pack | Claude first; Build AI for Desk badges |
| Resizable chat | Build AI |
| Project folders | Both |

---

## 17. Promotion path

1. Idea surfaces in chat (often while something is rendering or another batch is coding).
2. Capture / refine in **this file** (`Claude_Suggestions.md`).
3. When agreed, write it into **`Product_roadmap.md`** as Phase → Step → (later) Batch.
4. When building, open a **handoff** batch: implement, sync, verify, human-in-the-loop test.
5. Mark the Step/Batch done on the roadmap; leave the suggestion text for history unless it confuses — prefer append, don’t silently rewrite Owner intent.

---

## 18. Review questions for Build AI (Claude, 2026-09-29)

**From:** Claude, after reading this file and `Product_roadmap.md` side by side. **Asked by:** Owner, who wants Build AI to check these against its own log and verify them. Nothing earlier in this file or in the roadmap was changed for this review; it's appended as a record.

**How to answer:** reply under each question with **Agree / Disagree / Already handled**, a short reason, and (if agreed) which doc changes: roadmap Step, handoff Batch, or a correction note here. Owner makes the final call on anything marked **Owner decides**.

### 18.1 Sequencing (these change what ships in beta)

**Q1. Should recipes move from Phase 2 into Phase 0?**
- **Now:** the roadmap has `.recipe.json` as P2-S0.
- **Concern:** every clip the agent splices during Phase 0 and 1 (all beta users' work) could then never be reopened with its joins or audio lines. Section 12.8 already warns about this.
- **Cost:** small. A JSON write inside the existing splice and mix tools, with no UI.
- **Proposal:** fold recipe writing into **P0-S6 (AI post tools)**. P2-S0 then only reads recipes.

**Q2. Should the project folder layout (section 13) land before the public beta?**
- **Now:** the roadmap has it in Phase 2, "if not done earlier".
- **Concern:** renaming `clips/`, `final/` and `rejected/` after users have real projects means migrating their files. The layout also feeds the guided tour (P1-S2), media locate/move (P0-S1) and the MCP delivery paths.
- **Proposal:** the **folder names and the MCP mapping (13.5)** go in Phase 1, or late Phase 0. Keep button, Finish project and Send to game can wait.

**Q3. Should adult-content hiding and program packs be required for beta, not "as needed"?**
- **Now:** P1-S4 reads "Content & packs (as needed)", and Phase 1 says "NSFW hidden unless toggled (when that Step ships)".
- **Concern:**
  - Section 1 records Owner's decision that NSFW stays hidden unless turned on. The MCP side has to enforce it too, or Cursor and Jan users still see the tools.
  - Without packs, dual-PC users see Wan2GP tools that can't work, which breaks Owner's "no dead parts" rule.
- **Proposal:** make P1-S4 a required Step for beta. **Owner decides.**

### 18.2 Gaps in the roadmap

**Q4. Where does the Krita hand-off go?**
- The north star and the Phase 1 docs name Krita as the human-driven path.
- No Step schedules the Krita pack (`open_in_krita`, `krita_status`, `recommend_krita_models`, `write_krita_style`, `check_krita_readiness`), and section 14 questions 2–4 are still open.
- Phase 1 (docs only) plus Phase 2 (tools)? Or tools in Phase 1?

**Q5. Batch 6 and batch naming.**
- Both docs say "Batch 6 = Storyboard / FLF UX", but `desk-ui/CODE_FIX_HANDOFF.md` has no Batch 6. Is it logged somewhere else, or not opened yet?
- The roadmap proposes names like `P0-S2-B1`, while the handoff uses "Batch N". Which scheme is used from here on? Mixing both will confuse the log.

**Q6. Rin teaser: where does the audio come from, and is the example kept?**
- P0-S7 needs a Japanese hello, breeze and footsteps. Options:
  - **Kokoro:** CPU on the main PC, no GPU lock.
  - **MOSS:** ComfyBox; needs Owner's explicit go-ahead.
- Section 14 question 6 still asks whether to keep or archive "the Rin storyboard example", though it's now the teaser and guide. Close that question?

**Q7. Should the undo journal (section 7) be promoted?**
- It's a reliability feature, and Phase 0 is about reliability. It covers recycles, moves, renames and ships into `game/`.
- Bulk-action confirms and diagnostics export are the same kind of work. Promote them to Phase 0 or 1, or deliberately leave them out?

**Q8. Two wording issues in the roadmap.**
- Phase 0 is "pre-release" and also "tools that most users will never leave". Suggest: "the core most users won't need to go beyond."
- Phase 2 Blender: "Grok-key users may see MCP tools earlier". What does this mean?

### 18.3 Out-of-date or contradictory text in this file

Append-only is the rule, so these are listed, not fixed. Build AI: confirm each one, then either add a correction note under the section or tell Owner a rewrite is safe.

**Q9. Section 12.8 uses "Phase 0–4" for editor stages.**
- This clashes with the Phase / Step / Batch grammar and with the roadmap's P2-S0 to P2-S4. The "(phase 2)" and "(phase 3)" tags in the 12.1 table are the same problem.
- Relabel them as Steps?

**Q10. The save rules contradict each other.**
- 12.0.1 says "Nothing is overwritten" and refuses a used name, but its second row allows re-saving the same name (recycling the old one).
- 12.6 `timeline_save` refuses used names.
- Which rule wins? Claude's suggestion: refuse used names, and offer **Save as `<name>_v2`** instead.

**Q11. Stale paths and formats from before sections 12.13 and 13.**
- 12.0 step 7 still says "writes a new MP4"; it should follow the format choice.
- 12.2 still points the media bin at `clips/` and `audio/`; it should be `Video/` and `Audio/`.
- 12.5 still puts timelines in `edits/`; it should be `Post Production/`.

**Q12. The guide text still describes the old Rin.**
- 12.10 lists the English lines ("Greetings…") and a missing lunge clip as gaps.
- Section 1 now says the guide is rebuilt as bow + breeze + footsteps + JP hello.

**Q13. Is preview in the right Step?**
- P2-S4 and 12.8 put "Play video + sound" after the audio editor.
- 12.12 treats preview as part of audio work, and an audio editor you can't hear is hard to use.
- Fold basic preview into **P2-S3** and keep only the polish (loop section, post-save check) for P2-S4?

**Q14. The 0.25 s arrows assume 16 fps.**
- At 16 fps, 0.25 s is 4 frames, and at 24 fps it's 6. At 30 fps it's 7.5, which doesn't land on a frame line.
- Round each step to the nearest frame, or define the arrow step in frames (4 frames at 16 fps, 8 at 30)?

**Q15. Condensed Owner decisions in section 1.**
- The row "Timeline / audio nudge / MP4 vs WebM / Combine-Split … stay documented" replaced several separate Owner decisions and is credited "Owner + Claude".
- The originals and their credit still live in 12.11–12.14, so nothing is lost.
- Section 17 says to prefer append over rewriting Owner intent. Keep the condensed row, or restore separate Owner rows?

### 18.4 Minor

- **Q16.** Section 7.1 remembers chat widths per mode, including Editing; P0-S2 lists Document, Image and Video only. Build the setting so new modes can be added later?
- **Q17.** The section 1 row "`D:\Extra Models\` is the owner's Invoke canvas test bench, not an app install target" fits Owner's rule that owner models go there. Would "owner's personal models; the app never installs there" be clearer?

### 18.5 Build AI answers

*(Build AI / Composer, 2026-09-29 — answers for Owner + Claude. Owner still decides on Owner-decides items.)*

| # | Answer | Doc change |
|---|--------|------------|
| **Q1** | **Agree.** Write `.recipe.json` in existing splice/mix tools under **P0-S6**. Phase 2 only needs read/open UI. | Roadmap: P0-S6 includes recipe writes; P2-S0 = “consume recipes / open in editor.” |
| **Q2** | **Agree.** Folder **names + MCP mapping (13.5)** before public beta (late P0 or P1). Keep / Finish project / Send to game can wait. | Roadmap: new **P1-S0** (or P0-S8) “Project folder names + path map.” |
| **Q3** | **Agree (recommend required).** NSFW hide + packs for beta matches Owner “hidden unless on” and “no dead parts.” | Roadmap: P1-S4 required, not “as needed.” **Owner decides** final. |
| **Q4** | **Phase 1:** docs + `open_in_krita` / `krita_status`. Style recommend/write can land late P1 or early P2 once §14 Q2–4 answered. | Roadmap: **P1-S7 Krita hand-off (minimal).** |
| **Q5** | **Already handled / clarify.** Batch 6 **is** in `desk-ui/CODE_FIX_HANDOFF.md` (Storyboard/FLF + follow-ups). Going forward: handoff title **`Batch N — P0-Sx-By: …`** so both schemes appear once. | Handoff naming note; roadmap Batch log pointer. |
| **Q6** | **Kokoro** for JP hello + simple SFX if needed (CPU, no ComfyBox). **Keep** Rin example (close §14 Q6 as keep/teaser). MOSS only if Owner explicitly says. | Roadmap P0-S7 note; Suggestions §14 Q6 → answered keep. |
| **Q7** | **Phase 1**, not P0 critical path. Undo journal + bulk confirm + diagnostics = beta reliability, after prove chain. | Roadmap: **P1-S8 Undo journal & safety UX.** |
| **Q8** | **Agree** reword Phase 0 goal. “Grok-key users” = any MCP host (Cursor/Jan) with tools enabled can see Blender tools before Desk UI surfaces them — not Desk-Grok-specific. | Roadmap wording fix. |
| **Q9** | **Agree.** Relabel editor build stages as **Editor Steps E0–E4** (not “Phase”). | Correction note under §12.8; roadmap already uses P2-S*. |
| **Q10** | **Agree.** Prefer **refuse used name + offer `Save as …_v2`**. Same-name overwrite only via explicit “Replace (recycle previous).” | Correction note §12.0.1 / 12.6. |
| **Q11** | **Agree.** Stale `clips/` / `edits/` / “MP4 only” — correction notes until §12 rewrite. | Append notes; full rewrite when Editing Step starts. |
| **Q12** | **Agree.** Guide text should match bow + JP hello plan; English three-liner is historical. | Correction under §12.10. |
| **Q13** | **Agree.** Basic Play video+sound in **P2-S3**; polish loop-section / post-save check in P2-S4. | Roadmap P2-S3/S4. |
| **Q14** | **Agree.** Nudge in **whole frames** (default 4 frames @ 16 fps ≈ 0.25s); Shift = 1 frame. Never 7.5-frame steps. | Correction §12.12. |
| **Q15** | **Keep condensed row** + “details in 12.11–12.14.” Restoring duplicate rows adds noise. | No change. |
| **Q16** | **Agree.** Persist chat widths as a map keyed by mode id so Editing can be added later. | When P0-S2 ships. |
| **Q17** | **Agree.** Prefer: “Owner personal models path (`D:\Extra Models\`); the app never installs keepers there.” | Section 1 wording optional polish. |

**Push readiness (same day):** Suggestions + Roadmap live in both repos (MCP root canonical; One Desk copies with local `CODE_FIX_HANDOFF` links). Remotes: studio-agent → `private` (`Private-Studio`, tip branch `comfybox-cuda-5090` via orphan snapshot); One Desk → `origin` (`OneDesk` `main`). Prefer `git push`; `gh` auth may still need refresh for PR/issue CLI.

### 18.6 Correction notes (Build AI, append-only — do not rewrite §12 yet)

- **§12.8:** Call build slices **Editor Steps E0–E4**, not “Phase 0–4,” to avoid clashing with product Phases.
- **§12.0.1 / §12.6:** Prefer refuse duplicate names + offer `_v2`; explicit replace recycles the previous file.
- **§12.0 / §12.2 / §12.5:** Prefer `Video/`, `Audio/`, `Post Production/` and format choice from §12.13 / §13 when Editing ships.
- **§12.10 guide:** Target clip is bow + breeze + footsteps + JP hello (Kokoro); English three-liner / missing lunge are historical gaps.
- **§12.12:** Nudge in whole frames (default 4 @ 16 fps); Shift = 1 frame.
- **§7.1 / P0-S2:** Store chat widths as a mode-id map so Editing can be added later.

