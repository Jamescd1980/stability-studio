# Public export policy

Public remote: `origin` → `https://github.com/Jamescd1980/stability-studio.git`  
Private remote: `private` → `https://github.com/Jamescd1980/Private-Studio.git`

## Allowed on public

- MCP server code, general tools/docs
- NSFW **workflow JSON** and runner **scripts** (under `scripts/nsfw/` if you choose to publish them)
- Catalog entries that reference public Civitai model **IDs/URLs** (not the weight files)
- Style-lane / character LoRA **metadata** (triggers, file names) without redistributing `.safetensors`

## Never on public (or private git)

- API keys / tokens (`config.yaml` with secrets — gitignored; use `config.yaml.example`)
- Generated **images/videos** (especially NSFW gens)
- Model weight blobs (`.safetensors`, large checkpoints)
- Orla phonetic WAVs, gallery state, MCP `outputs/` media

## Scrub checklist before `git push origin`

1. Grep staged tree for `api_key`, `token`, `password`, `CIVITAI`.
2. Confirm no `*.png` / `*.mp4` under delivery or `outputs/`.
3. Prefer placeholders for home LAN IPs in public docs (`YOUR_LAN`) when possible.
4. Easy omit: drop `scripts/nsfw/` if you want a SFW-only public slice.
5. Do **not** blind-push private `main` to `origin` — export selectively.

## Private vs public

| | Private | Public |
|--|---------|--------|
| NSFW scripts | Yes (`scripts/nsfw/`) | Optional |
| NSFW workflows | Yes | Yes (your choice) |
| NSFW images | No (never in git) | No |
| API keys | No | No |
| Myra LAN handoff | Yes | Prefer placeholders / omit |
| Download-and-go | `SETUP.md` | Partial / scrubbed |

Restore after wipe: clone **private**, follow [`SETUP.md`](SETUP.md).
