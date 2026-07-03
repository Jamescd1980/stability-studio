# Jan Studio Copilot — remote desktop generation

Paste into **Studio Copilot** instructions on the **laptop**.

---

## Remote generation (desktop GPU)

This machine does **not** run ComfyUI. GPU work is on **<DESKTOP_HOSTNAME>** (`<DESKTOP_LAN_IP>`).

1. `stability-studio__get_generation_context` — confirm ComfyUI reachable (session start)
2. **Before each prompt:** `stability-studio__get_prompt_style(style=...)` or `platform=illustrious|pony|flux|wan_image`
3. Brainstorm: `stability-studio__log_image_prompt` (no GPU)
4. Generate: `stability-studio__generate_image` (catalog style: `ilustmix`, `juggernaut`, …)

### Paths

| What | Where |
|------|-------|
| Project | `Z:\` (mapped share) |
| Prompt log | `Z:\logs\prompt_log.jsonl` |
| Images | `Z:\images\` |

### Rules

- Do **not** call `download_style_assets`, `setup_image_editing`, or `generate_video_hero` from the laptop
- After `log_image_prompt`, offer `generate_image` when the user approves
- Use `list_image_prompt_log` for prior prompts by `scene_id`

Reference: `config-examples/laptop-remote/README.md`

---
