# Storyboard spreadsheet — book chapter → VN

Spreadsheet-driven storyboards for **book → visual novel** work. One CSV per chapter is the source of truth; agents (Cursor, Open Interpreter, Jan) help fill prompts and run MCP generation; Ren'Py skeleton exports when you are ready to code.

## Your workflow (with AI)

```
Chapter text (source/)
        ↓  you + AI walk the chapter
storyboard/ch01_storyboard.csv   ← edit in Excel / Sheets
        ↓  fill prompt_positive, set status=prompt_ready
MCP generate_image / video / audio  ← labeled paths from sheet
        ↓  mark status=approved
check_storyboard_sheet
        ↓
export_renpy_skeleton → renpy/generated/
        ↓  human review + Ren'Py beta
ship chapter → next chapter
```

## Project layout

Uses the same delivery folder as [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) (`outputs.delivery` in `config.yaml`).

Your book project (set `outputs.delivery` in `config.yaml`):

`<PROJECT_DELIVERY_DIR>/`

| Path | Purpose |
|------|---------|
| `source/` | Book PDF, chapter extracts |
| `storyboard/ch01_storyboard.csv` | **Scene spreadsheet** (one row = one VN beat) |
| `images/ch01_003_dialogue.png` | Named from `image_asset` column |
| `clips/ch01_004_video.mp4` | Fight / motion rows |
| `audio/ch01_003_dialogue_rin.mp3` | MOSS lines |
| `renpy/generated/` | Auto skeleton `.rpy` files |
| `logs/storyboard_manifest.json` | Optional — hero video splice (Rin path) |

## CSV columns

| Column | Meaning |
|--------|---------|
| `scene_id` | Stable id — drives filenames (`ch01_003_dialogue`) |
| `chapter` / `sequence` | Sort order |
| `type` | `still`, `background`, `sprite`, `dialogue`, `narration`, `video`, `sfx`, `choice`, `transition` |
| `location` / `characters` | Scene context for prompts |
| `action` | Visual description (for you + AI) |
| `dialogue` / `speaker` | Spoken line + Ren'Py character |
| `image_asset` | Target path e.g. `images/ch01_002_still.png` |
| `video_asset` / `audio_asset` | Clip / MOSS targets |
| `style` | MCP style id (`ilustmix`, `pony`, `juggernaut`) |
| `prompt_positive` / `prompt_negative` | Generation prompts |
| `status` | `planned` → `prompt_ready` → `approved` |
| `notes` | Human reminders |

Template: `stability-studio-mcp/scripts/storyboard/examples/ch01_storyboard.template.csv`

## CLI

```powershell
cd D:\studio-agent\stability-studio-mcp

# New chapter sheet (3 starter rows)
python scripts\storyboard\manage_sheet.py init --chapter 1 --title "Chapter 1" `
  --project-dir "<PROJECT_DELIVERY_DIR>"

# After you fill prompts and generate assets
python scripts\storyboard\manage_sheet.py check --chapter 1 `
  --project-dir "<PROJECT_DELIVERY_DIR>"

# What MCP should run next
python scripts\storyboard\manage_sheet.py queue --chapter 1 `
  --project-dir "<PROJECT_DELIVERY_DIR>"

# Ren'Py skeleton
python scripts\storyboard\manage_sheet.py export-renpy --chapter 1 `
  --project-dir "<PROJECT_DELIVERY_DIR>"
```

## MCP tools (Cursor / OI)

| Tool | Use |
|------|-----|
| `init_storyboard_sheet` | Create `chXX_storyboard.csv` |
| `check_storyboard_sheet` | Validate rows + files on disk |
| `list_storyboard_generation_queue` | Next `generate_image` / hero video / MOSS jobs |
| `export_renpy_skeleton` | Write `renpy/generated/chXX_script.rpy` |
| `get_project_context` | **Session start** — phase, blockers, recent agent log |
| `init_project_context` | One-time per project |
| `update_project_context` | **Session end** — phase, next actions |
| `append_project_log` | One line: what this agent just did |
| `log_image_prompt` | Save brainstorm prompt to `logs/prompt_log.jsonl` (Jan Prompt Lab) |
| `list_image_prompt_log` | Search prompt history |
| `generate_image` | Use `target` path from queue; save to `image_asset` |
| `plan_storyboard_scene` | Short **video-only** beat scripts (Rin-style) |

## Session with Cursor or OI

**Start every session:** `get_project_context` (or read `logs/project_context.json` + tail of `logs/agent_backlog.jsonl`).

**End every session:** `update_project_context` + `append_project_log` for what you changed.

1. Open chapter text from `source/` (paste or extract).
2. Ask: *"Add rows to ch01_storyboard for each scene — dialogue, stills, one fight video."*
3. Review CSV in Excel; tweak `action` / `dialogue`.
4. Ask: *"Fill prompt_positive for all `planned` still rows, illustmix style."*
5. Set `status=prompt_ready`.
6. Ask: *"Run list_storyboard_generation_queue and generate_image for each row; update status when saved_files match image_asset."*
7. `export_renpy_skeleton` → open in Ren'Py SDK → beta test.

## Status lifecycle

```
planned        → row exists, no prompt yet
prompt_ready   → prompts filled, ready for MCP
generating     → agent marked in-flight (optional)
review         → file exists, you are judging quality
approved       → locked for Ren'Py export
rejected       → moved to rejected/; row kept for history
skip           → no asset needed
```

## What this does *not* do yet (roadmap)

- PDF → auto-split chapters (book is in `source/`; manual paste for now)
- Direct Ren'Py project scaffold (skeleton only)
- Auto-update CSV from MCP results (agent updates rows manually)
- Lip-sync column wiring to Infinitetalk

## Agent context backlog

| File | Role |
|------|------|
| `logs/project_context.json` | **Snapshot** — phase, active chapter, blockers, next actions, agent last_seen |
| `logs/agent_backlog.jsonl` | **Append-only log** — who did what, with artifact paths |
| `logs/prompt_log.jsonl` | **Prompt history** — brainstorm + generation params + output paths |
| `storyboard/chXX_storyboard.csv` | **Scene truth** — not replaced by context file |

Chat history (Cursor/Jan) is not shared across apps. The backlog lives **in the project folder** so any agent with MCP or file access sees the same state.


The **Rin** pipeline (`storyboard_manifest.json` + Wan2GP splice) is for **short hero video reels**. The **spreadsheet** is for **full VN chapters** (mostly stills + selective video). Use both: manifest for a fight trailer; sheet for the playable chapter.
