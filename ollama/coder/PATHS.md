# Path bible — Nari (create) ↔ Coder on Orla (install)

**Orla** = this Windows PC (`192.168.50.42`). **Coder** = the coding OI profile on Orla. **Nari** = ComfyBox create.

## Roots

| Kind | Path | Who writes |
|------|------|------------|
| Review stills | `D:\ComfyBox Images and Videos\Images\` | Nari / MCP |
| Review video | `D:\ComfyBox Images and Videos\Video\` | Nari / MCP |
| TheaterJobs staging (candidates) | `D:\Bad boy\TheaterJobs\staging\candidates\` | Nari/coder until approved |
| TheaterJobs approved masters | `D:\Bad boy\TheaterJobs\staging\approved\` | After human approve |
| Game images (shipped) | `D:\Bad boy\TheaterJobs\game\images\` | Coder **only after you say ship** |
| Game scripts | `D:\Bad boy\TheaterJobs\game\**\*.rpy` | Coder in workspace |
| Handoff note | `D:\Bad boy\TheaterJobs\staging\handoff.md` | Nari fills → coder reads |
| Path index (this file) | `D:\studio-agent\ollama\coder\PATHS.md` | Docs |

Unity (later): workspace = Unity project root; assets under `Assets/` only.

## Naming scheme (required)

```
{project}_{scene}_{beat}_{view}_{stage}.{ext}
```

| Part | Rules | Example |
|------|--------|---------|
| project | lowercase, no spaces | `dasbooty` |
| scene | 2-digit or short id | `01` |
| beat | short snake | `strip`, `doggy`, `creampie` |
| view | `front` `side` `rear` `pov` | `front` |
| stage | still: `dressed` `topless` `naked` `…`; video: `v1` `take2` | `dressed` |

Examples:
- `dasbooty_01_strip_front_dressed.png`
- `dasbooty_01_strip_front_naked.png`
- `dasbooty_03_doggy_pov_v1.mp4`

Use MCP `suggest_asset_name(...)` if unsure.

## Coder sandbox

Open Interpreter workspace = project folder (e.g. TheaterJobs). Coder may:

- Read/write under that workspace
- **Read** delivery Images/Video (copy into staging/game — never invent new delivery trees)
- **Not** call Wan/Forge/generate_image
- **Not** hard-delete (Recycle only if a tool exists)

## GPU on Orla

**Coder owns the 5060 Ti** (Ollama GPU). No CPU fallback. No Invoke↔coder “split” — diffusion/create lives on **ComfyBox/Nari** (that’s where unload-before-Wan happens).
