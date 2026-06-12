# Release — Stability Studio 1.0.0-beta

**Date:** 2026-06-12  
**Tag:** `v1.0.0-beta`

Beta release of Stability Studio MCP: local image/video generation for Stability Matrix + ComfyUI, with **Wan2GP hero storyboards** and a unified storyboard CLI.

## Highlights

| Area | What ships |
|------|------------|
| **Images** | `generate_image`, `edit_image`, four art food groups |
| **Draft video** | ComfyUI Wan 2.2 TI2V-5B (`i2v_5b`, `v2v_5b_painter`) |
| **Hero video** | Wan2GP Lightning v2 (`generate_video_hero`) |
| **Audio** | MOSS-TTS (`generate_audio`) |
| **Storyboard** | MCP `plan_storyboard_scene` + CLI `generate_storyboard.py` |
| **Reference** | Rin kitsune scene — [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) |

## Install

```powershell
git clone https://github.com/Jamescd1980/stability-studio.git
cd stability-studio
.\install.ps1
copy stability-studio-mcp\config.yaml.example stability-studio-mcp\config.yaml
# Edit paths — set outputs.delivery for storyboard projects
```

Enable MCP in Cursor (see [CURSOR-INTEGRATION.md](CURSOR-INTEGRATION.md)).

## Storyboard quick test (Rin-style)

```powershell
cd stability-studio-mcp
python scripts/storyboard/generate_storyboard.py plan ^
  --title "rin_demo" ^
  --script "walk toward camera | Greetings." ^
  --clip-template "clips/Rin_clip{index}_walk.mp4"
python scripts/storyboard/generate_storyboard.py check
# After hero clips exist:
python scripts/storyboard/generate_storyboard.py splice
```

MCP path: `check_storyboard_readiness` → `plan_storyboard_scene` → `generate_video_hero` per beat → `generate_audio` → CLI `splice`.

## Handoff zip (no git)

```powershell
python stability-studio-mcp/scripts/build_handoff_zip.py
# -> studio-agent.zip at repo root
```

## Requirements

- NVIDIA GPU (16 GB validated for draft + hero with exclusive backend policy)
- Stability Matrix + ComfyUI
- Wan2GP package for hero I2V (Stability Matrix)
- Large model downloads per [WAN-ASSETS.md](WAN-ASSETS.md)

## Known limits (16 GB)

- Do not run ComfyUI and Wan2GP GPU jobs concurrently
- Hero clips: ~49 frames @ 832×480 recommended
- Infinitetalk lip sync optional and VRAM-heavy — prefer hero splice without lipsync

## GitHub release checklist

1. Verify `config.yaml` is **not** committed
2. Run `python scripts/clean_outputs.py` if `outputs/` has loose artifacts
3. Run `python scripts/build_handoff_zip.py`
4. Tag: `git tag v1.0.0-beta`
5. Attach `studio-agent.zip` to GitHub release (optional)
6. Paste [CHANGELOG.md](CHANGELOG.md) section into release notes
