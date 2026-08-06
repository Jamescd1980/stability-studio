# Media delivery layout

**Root:** `D:\ComfyBox Images and Videos`

Owner rule: images under `Images\`, video under `Video\`, user drops in `User Import\`. Scene work lives under **Theater Jobs** with clear `Work` vs `Completed Scene`.

## Tree

```
D:\ComfyBox Images and Videos\
  User Import\                          # human drops for the agent
  Images\
    Theater Jobs\
      Elven Appetite\
      Pale Elf Rider\
      Where the Wild Fern Moans\
        Stills\                         # keepers / working CGs
      Saloon\
  Video\
    Theater Jobs\
      Elven Appetite\
        Completed Scene\
        Work\
      Pale Elf Rider\
        Completed Scene\
        Work\
      Where the Wild Fern Moans\
        Completed Scene\                 # game-ready loops only
        Work\                            # raw gens + experiments
          frames_extract\
          ebsynth\
          forge_refine\
          seedvr\
          splice\
      Saloon\
        Completed Scene\
        Work\
  temp\<job_name>\                      # scratch; delete when done
  audio\
  logs\
```

## Naming

| Bad | Good |
|-----|------|
| `Video\studio_agent_wan22_moe_00133.mp4` left forever | `Video\Theater Jobs\Where the Wild Fern Moans\Work\kiss_00133_raw.mp4` |
| `Images\proof_queue\fern_darkness\...` | `Images\Theater Jobs\Where the Wild Fern Moans\Stills\` |
| `Fern -Darkness\` | scene name above |
| `temp2`, `test`, `_mcp_...` forever | `temp\ebsynth_kiss_00133\` then clean up |

Engine / Forge may land as `studio_agent_*` or temp names in `Video\` / `Images\` root (or Forge output). **That is fine as a landing zone** — promote ASAP into the scene folder with a readable stem, then recycle duplicates.

**Do not** leave keepers in `User Import\` (human drops only), `Video\Frieren\...` (legacy), or scattered `review\` / `hero_forge\` working trees after promote.

| Scene | Images | Video |
|-------|--------|-------|
| Elven Appetite (BJ) | `Images\Theater Jobs\Elven Appetite\Stills\` | `Video\Theater Jobs\Elven Appetite\{Work\|Completed Scene}\` |
| Pale Elf Rider / Saloon | `Images\Theater Jobs\Saloon\Stills\` | `Video\Theater Jobs\Saloon\{Work\|Completed Scene}\` |
| Where the Wild Fern Moans | `Images\Theater Jobs\Where the Wild Fern Moans\Stills\` | `Video\Theater Jobs\Where the Wild Fern Moans\{Work\|Completed Scene}\` |

## Completed Scene

Only clips approved for the game / packaging. Install from here into `D:\Bad boy\TheaterJobs\game\videos\...` (or staging).

## MCP note

`list_media_paths` / `outputs.layout` still map `clips → Video`, `images → Images`. Scene subfolders are house convention on top of that — not auto-created by Comfy download yet.
