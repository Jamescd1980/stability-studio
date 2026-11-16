# Plan: Orla-PC + coder + handoff

Status: **Phases 0–5 implemented** (2026-09-22).

## Goals (locked)

| Name | Meaning |
|------|---------|
| **Orla** | Windows PC host name |
| **Nari** | Create on ComfyBox |
| **Coder** | Ren’Py install on Orla 5060 Ti |
| **Myra** | Pi voice |

## Phase checklist

### Phase 0 — Scrub old Orla persona — DONE
- [x] `ollama/orla/README.md` rewritten (PC name; persona retired)
- [x] Handoff comments / `ask_orla` tool text updated
- [x] OI: Coder profile added; default stays **Nari**; old orla profile may still exist in config but is not default
- [x] No VLM required

### Phase 1 — Path bible + naming — DONE
- [x] `ollama/coder/PATHS.md`
- [x] MCP `suggest_asset_name`
- [x] Nari skill delivers to Images/Video + naming scheme

### Phase 2 — Lessons append — DONE
- [x] MCP `append_lesson`
- [x] Nari skill documents it

### Phase 3 — Coder on Orla — DONE
- [x] Ollama installed; **`qwen3-coder:30b`** → `coder:latest` (was qwen2.5-coder:14b)
- [x] Modelfile, skill, `configure_open_interpreter.py`, `gpu_etiquette.ps1`
- [x] Toolcall proxy `:11436` + OI profile `custom:coder-orla`
- [x] No Wan/Forge on coder skill

### Phase 4 — Handoff ritual — DONE
- [x] `D:\Bad boy\TheaterJobs\staging\handoff.md`
- [x] Doc id `handoff` / `path-bible` in `list_studio_docs`

### Phase 5 — Nice-to-haves — DONE
- [x] `fetch_web_documentation` (allowlisted hosts)
- [x] `read_studio_doc(..., query=)` keyword chunks
- [x] Audio/polish ownership noted in Nari skill (Nari makes; Coder wires)
- [x] JSON validation remains inside existing MCP tools

## How to use

1. **OI → Nari** — create; name via `suggest_asset_name`; fill `staging/handoff.md`
2. **OI → Coder** (profile) — open TheaterJobs workspace; read handoff; wire `.rpy`
3. Before Invoke: `.\ollama\coder\gpu_etiquette.ps1 invoke-free`
4. Restart OneDesk MCP so new tools appear

## Done earlier (Nari GPU)

- Slim Modelfile; 5090 when free; unload before Wan
