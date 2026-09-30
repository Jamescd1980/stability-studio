# Product roadmap — One Desk + Stability Studio MCP

**Status:** Living plan. Next target = **Phase 0** (finish what is in front of us).  
**Updated:** 2026-09-29 (Owner + Build AI + Claude; §18 Build AI answers applied).

## Doc roles

| Doc | Use for |
|-----|---------|
| [`Claude_Suggestions.md`](Claude_Suggestions.md) | Conversation, idea refinement, teasers, “what if.” Non-coding communication. |
| **`Product_roadmap.md` (this file)** | Final plan: **Phase → Step → Batch**. Focus on the current Phase. |
| [`CODE_FIX_HANDOFF.md`](CODE_FIX_HANDOFF.md) *(One Desk repo)* / `desk-ui/CODE_FIX_HANDOFF.md` *(monorepo checkout)* | Designed/coded work that still needs **implement and/or verify** + human-in-the-loop testing. |

Ideas may appear during renders, tests, or while an AI is mid-build. What sticks is promoted: Suggestions → this roadmap → handoff batches.

## Grammar

| Word | Meaning | Example |
|------|---------|---------|
| **Phase** | Big picture — product era / release story | Phase 1 = first public beta |
| **Step** | Medium picture — workstream inside a phase | Step: resizable chat |
| **Batch** | Small picture — shippable engineering slice (commit-sized) | `Batch 6 — P0-S1-B6: Storyboard / FLF UX` |

- Phases get marketed. Steps get planned here. Batches get coded, handed off, and verified.  
- Handoff titles: **`Batch N — Px-Sy-Bz: short name`** so old “Batch N” and new roadmap ids stay aligned.  
- Prefer many small batches over one upgrade that takes a week to unbreak.  
- Manual Editing UI build stages (Suggestions §12) are labeled **Editor Steps E0–E4**, not Phases.

---

## North star (all phases)

**Primary:** AI-driven art, MCP, One Desk UI.  
**Secondary:** Ren'Py / game WebM export, full draw suites.  
**Ship shape:** One Desk (UI box) + MCP (MCP box); both required. ComfyUI, Forge, Wan 2.2, Krita, and Comfy vs Stability Matrix are user-installed, with soft guidance from local hardware (PC / RAM / GPU / VRAM).

**Workflow story:** Headless ComfyUI + One Desk = AI-driven. Krita = human-driven paint. Both can share headless Comfy; the agent helps with workflows, checkpoints, LoRAs, and prompts to paste.

---

## Phase 0 — Pre-release (current target)

**Goal:** The **core product most users will not need to go beyond** — local AI writing, prompting, storyboarding, and image/video gen, with a stable UI.

### Outcomes
- AI-guided **writing**, **prompting**, **storyboarding**, **image / video gen** on a local PC (and dual-PC where already supported).
- Recommended **checkpoints and LoRAs** for style (pose control = optional / maybe).
- Recommended **local AI models** by task and purpose; awareness of local assets.
- **Stable UI** — no crash loops, lost jobs, or “clip finished but invisible” class bugs.
- Soft hardware guidance (VRAM tiers, single vs dual PC).
- AI post tools write **recipes** beside outputs (no Editing UI yet).

### Steps (Phase 0)

| Step | Intent | Notes |
|------|--------|--------|
| P0-S1 Reliability & media | Jobs finish → paths resolve → filmstrip / scopes show nested Video & Images; move-to-folder; Seed/Still notes; FLF / storyboard UX | Handoff Batches 1–6+; keep proving |
| P0-S2 Resizable / collapsing chat | Enlarge viewer; remember width per **mode id** (Document / Image / Video; Editing later) | **Verified** Batch 7 (2026-09-30) — handoff `P0-S2-B1` |
| P0-S3 Workflows end-to-end | Writing → prompt → still → Forge → Wan → AI post tools prove on this rig | Human-in-the-loop keepers |
| P0-S4 Style & model guidance | Checkpoint / LoRA recommendations; task-based brain hints | Catalog + docs; pose control optional |
| P0-S5 Guided tour foundation | Onboarding path that will ship in Phase 1 | Drafts OK in Phase 0 |
| P0-S6 AI post tools + recipes | Group existing MCP splice, ping-pong, mix, frame grab; **write `.recipe.json`** on agent/editor outputs | **Recipe writes verified** Batch 8 (2026-09-30); mix/frame grab later; P2 reads recipes |
| P0-S7 Minimal Rin teaser clip | Bow + breeze + footsteps + JP hello on bow; honest README | **Kokoro** for VO (CPU); keep Rin example |
| P0-S8 Folder names (optional late P0) | Align default folder names / MCP map with Suggestions §13.5 | Or slip to P1-S0; before public beta either way |

### Explicitly out of Phase 0
- Manual Video / Audio **Editing** pane (Suggestions §12 teaser / Phase 2).
- Ren'Py-first export defaults.
- Blender in One Desk UI (MCP tools may exist; Desk surfacing later).
- Full Kokoro PTT / STT / recording suite.
- Forge face-highlight UI / light inpaint productization.
- Full undo journal (see P1-S8).

---

## Phase 1 — First public beta

**Goal:** Nice neat package people can install and follow.

### Outcomes
- Stable UI + proven workflows from Phase 0.
- **Full guided tour** / setup guidance.
- Ship **only** our UI in the UI box and **MCP** in the MCP box (caveat: both needed).
- Docs: ComfyUI any install; soft Comfy vs Stability Matrix; headless Comfy + Desk vs Krita human path.
- **NSFW hidden unless toggled** (MCP-enforced, not UI-only).
- Program packs so dead tools (e.g. Wan2GP on dual-PC) do not show.
- Project **folder names + path mapping** before users accumulate unmigratable trees.

### Steps (Phase 1)

| Step | Intent |
|------|--------|
| P1-S0 Project folder names + MCP map | Suggestions §13.5 mapping; Keep/Finish/Send can wait |
| P1-S1 Package & installers | Versioned One Desk + MCP; manual update + rollback |
| P1-S2 Guided tour complete | Tiered setup; hardware soft-routing |
| P1-S3 Docs & programs list | README clean-up; works-with / tailored-for; agent-readable list |
| P1-S4 Content & packs (**required**) | Adult toggle + program packs / layouts |
| P1-S5 Notices & About | Third-party notices; version in app |
| P1-S6 Beta harden | Crash/diagnostics pass; human test checklist |
| P1-S7 Krita hand-off (minimal) | Docs + `open_in_krita` / `krita_status`; style write after §14 Q2–4 |
| P1-S8 Undo journal & safety UX | Action journal, bulk-confirm, diagnostics export |

### Explicitly out of Phase 1
- Manual Editing UI (tease in docs / “Coming next”).
- Blender Desk UI.
- Full voice chat / recorder product.

---

## Phase 2 — Depth (editors, Blender, voice)

**Goal:** Power users and audio/edit depth without rewriting Phase 1.

### Outcomes
- **Manual** video + audio editor panes + AI-assisted editing (Suggestions §12; mockup = behavior contract). Editor Steps **E0–E4**.
- Progress bar on long encodes; Save refuses used names and offers `_v2` (or explicit replace → recycle).
- Audio nudge in **whole frames** (default 4 @ 16 fps); Shift = 1 frame.
- Basic **Play video + sound** with the audio editor; polish after.
- Blender: MCP early OK; One Desk UI when ready (other MCP hosts may see tools before Desk surfaces them).
- Full **Kokoro** toolset; PTT; STT; audio recording.
- Project layout UX (Keepers / Finish) if not finished in P1.

### Steps (Phase 2)

| Step | Intent |
|------|--------|
| P2-S0 Consume recipes | Open clip/audio layout from `.recipe.json`; guessed joins only as fallback |
| P2-S1 Video editor UI (E1) | Editing button; Merge / Loop / Ping Pong; Save; unsaved rules |
| P2-S2 Film strip / cut / agent open (E2) | Joins, trim, review notes |
| P2-S3 Audio editor + basic preview (E3) | Forced save port; tracks; nudge; normalize; ducking; Combine / Split; **Play video + sound** |
| P2-S4 Preview polish (E4) | Loop section; post-save check; fades / auto-align as approved |
| P2-S5 Blender Desk surfacing | When ready |
| P2-S6 Voice suite | Kokoro + PTT + STT + record |

---

## Phase 3 — Control polish

**Goal:** Help Forge / light edit without becoming a paint app.

### Outcomes
- Face / region highlighting so Forge hits the right area.
- Light inpaint aids — **not** Krita or Invoke level unless demand + solid free code, or the product funds a draw suite.

### Steps (Phase 3)

| Step | Intent |
|------|--------|
| P3-S1 Face / region highlight UI | Drive Forge passes |
| P3-S2 Light inpaint aids | Minimal; hand off to Krita for real paint |
| P3-S3 Demand-driven extras | Only with evidence |

---

## Near-term focus (what is in front of us)

1. Finish **Phase 0** reliability and prove writing → still → Forge → Wan.  
2. Land **P0-S2** resizable / collapsing chat when UI bandwidth allows.  
3. Fold **recipe writes** into **P0-S6** as post tools are touched.  
4. Keep Suggestions §12 as **teaser**; no Editing UI batches until Phase 2.  
5. Rebuild **Rin bow + Kokoro audio** when ready for onboarding/marketing.  
6. Promote new ideas only after they stick in `Claude_Suggestions.md`.

---

## Batch log (pointer)

Engineering history: One Desk repo [`CODE_FIX_HANDOFF.md`](CODE_FIX_HANDOFF.md).  
New batches: **`Batch N — Px-Sy-Bz: title`**.
