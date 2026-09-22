# MCP tools (published inventory)

**Count: 138** tools registered via `@mcp.tool` in `stability-studio-mcp/server.py`  
**As of:** 2026-09-22 (matches this commit’s `server.py`)

> Agents: prefer **`get_onboarding_context`** (new setup) or **`get_generation_context`** (every generate turn) before browsing the full list. Thin clients (Jan, small local models) should use the **core allowlist** below — not all 138.

## Core allowlist (~24) — start here

| Group | Tools |
|-------|--------|
| **Context** | `get_onboarding_context`, `get_generation_context`, `list_styles`, `list_video_workflows`, `list_art_food_groups`, `get_prompt_style` |
| **Generate** | `generate_image`, `suggest_asset_name`, `resolve_style_lane` |
| **Edit** | `edit_image`, `plan_image_edit`, `setup_image_editing`, `check_image_editing_readiness` |
| **Video** | `generate_video`, `check_wan_assets`, `check_comfyui_dependencies` |
| **Health / lock** | `check_gpu_backend`, `comfy_queue_status`, `unload_nari_for_gpu`, `release_gpu_lock`, `check_backends` |
| **Assets** | `check_style_assets`, `download_style_assets`, `download_wan_assets` |
| **Docs** | `list_studio_docs`, `read_studio_doc`, `search_studio_docs` |

Everything else is **advanced** (Forge refine, pose/ControlNet, storyboard, polish/splice, delivery media, audio, Blender bridge, etc.). Discover via context tools or `TOOLS.md` full list — do not dump all 138 into a small-model tool schema.

## Groups (full surface)

### Context / catalog (discover first)
`get_onboarding_context`, `get_generation_context`, `get_project_context`, `init_project_context`, `update_project_context`, `get_prompt_style`, `list_art_food_groups`, `list_styles`, `list_checkpoints`, `list_loras`, `list_video_workflows`, `list_baked_in_characters`, `list_character_loras`, `list_character_mesh_assets`, `list_set_mesh_assets`, `list_solid_strip_maps`, `list_pose_control_options`, `list_nsfw_image_loras`, `list_studio_docs`, `list_source_images`, `list_media_paths`, `list_delivery_media`, `list_image_prompt_log`, `list_storyboard_generation_queue`, `list_kokoro_voices`, `reload_catalog`, `scan_models`, `sync_checkpoint_architectures`

### Generate
`generate_image`, `generate_image_guided`, `generate_image_i2i`, `generate_image_controlnet`, `generate_image_pose_guided`, `compile_image_prompt`, `suggest_asset_name`, `log_image_prompt`, `resolve_style_lane`, `resolve_character_loras`, `resolve_nsfw_scene_loras`, `lookup_character_identity`, `get_action_combat_playbook`

### Edit / refine / control
`edit_image`, `plan_image_edit`, `setup_image_editing`, `check_image_editing_readiness`, `inpaint_image`, `inpaint_advanced`, `setup_ip_adapter`, `check_ip_adapter_assets`, `check_ip_adapter_dependencies`, `install_ip_adapter_dependencies`, `download_ip_adapter_assets`, `setup_controlnet`, `check_controlnet_assets`, `check_controlnet_dependencies`, `install_controlnet_dependencies`, `download_controlnet_assets`, `download_sd15_controlnet_assets`, `setup_pose_control`, `check_pose_control_readiness`, `extract_control_maps`, `setup_face_detail`, `check_face_detail_dependencies`, `install_face_detail_dependencies`, `download_face_detail_assets`, `switch_stills_backend`, `generate_image_forge`, `refine_image_forge`, `check_forge_backend`

### Video / storyboard / polish
`generate_video`, `generate_video_hero`, `plan_wan_beat`, `plan_wan2gp_job`, `check_wan_assets`, `download_wan_assets`, `check_wan_video_loras`, `download_wan_video_loras`, `resolve_wan_action_loras`, `check_wan_prompt`, `check_wan2gp_assets`, `download_wan2gp_assets`, `check_wan2gp_runtime`, `check_painter_i2v_dependencies`, `install_painter_i2v_dependencies`, `check_hunyuan_assets`, `download_hunyuan_assets`, `gate_i2v_clip`, `extract_chain_lastframe`, `recommend_polish`, `polish_wan_video`, `polish_wan_best`, `interpolate_video`, `upscale_video_local`, `concat_video_clips`, `splice_pingpong`, `splice_crossfade_loop`, `splice_pose_matched_loop`, `check_ebsynth`, `check_local_post`, `plan_storyboard_scene`, `check_storyboard_readiness`, `check_storyboard_sheet`, `init_storyboard_sheet`, `plan_scene_sequence`, `generate_scene_sequence`, `export_renpy_skeleton`

### Audio
`generate_audio`, `check_moss_assets`, `download_moss_assets`, `check_kokoro_backend`, `generate_speech_kokoro`, `list_kokoro_voices`, `rewrite_chapter_phonetic`

### Health / GPU lock (keep visible)
`check_gpu_backend`, `comfy_queue_status`, `unload_nari_for_gpu`, `release_gpu_lock`, `check_backends`, `check_comfyui_dependencies`, `install_comfyui_dependencies`

### Delivery / media
`delivery_media_root`, `list_delivery_media`, `view_delivery_image`, `view_delivery_video_frame`, `copy_delivery_media`, `move_delivery_media`, `rename_delivery_media`, `open_delivery_in_explorer`, `recycle_delivery_media`

### Docs / lessons
`list_studio_docs`, `read_studio_doc`, `search_studio_docs`, `append_lesson`, `append_project_log`, `fetch_web_documentation`

### Blender bridge
`get_blender_workflow_playbook`, `register_blender_control_maps`

### Misc install helpers
`check_style_assets`, `download_style_assets`, `check_nsfw_image_loras`, `download_nsfw_image_loras`

## Alphabetical (complete)

```
append_lesson
append_project_log
check_backends
check_comfyui_dependencies
check_controlnet_assets
check_controlnet_dependencies
check_ebsynth
check_face_detail_dependencies
check_forge_backend
check_gpu_backend
check_hunyuan_assets
check_image_editing_readiness
check_ip_adapter_assets
check_ip_adapter_dependencies
check_kokoro_backend
check_local_post
check_moss_assets
check_nsfw_image_loras
check_painter_i2v_dependencies
check_pose_control_readiness
check_storyboard_readiness
check_storyboard_sheet
check_style_assets
check_wan2gp_assets
check_wan2gp_runtime
check_wan_assets
check_wan_prompt
check_wan_video_loras
comfy_queue_status
compile_image_prompt
concat_video_clips
copy_delivery_media
delivery_media_root
download_controlnet_assets
download_face_detail_assets
download_hunyuan_assets
download_ip_adapter_assets
download_moss_assets
download_nsfw_image_loras
download_sd15_controlnet_assets
download_style_assets
download_wan2gp_assets
download_wan_assets
download_wan_video_loras
edit_image
export_renpy_skeleton
extract_chain_lastframe
extract_control_maps
fetch_web_documentation
gate_i2v_clip
generate_audio
generate_image
generate_image_controlnet
generate_image_forge
generate_image_guided
generate_image_i2i
generate_image_pose_guided
generate_scene_sequence
generate_speech_kokoro
generate_video
generate_video_hero
get_action_combat_playbook
get_blender_workflow_playbook
get_generation_context
get_onboarding_context
get_project_context
get_prompt_style
init_project_context
init_storyboard_sheet
inpaint_advanced
inpaint_image
install_comfyui_dependencies
install_controlnet_dependencies
install_face_detail_dependencies
install_ip_adapter_dependencies
install_painter_i2v_dependencies
interpolate_video
list_art_food_groups
list_baked_in_characters
list_character_loras
list_character_mesh_assets
list_checkpoints
list_delivery_media
list_image_prompt_log
list_kokoro_voices
list_loras
list_media_paths
list_nsfw_image_loras
list_pose_control_options
list_set_mesh_assets
list_solid_strip_maps
list_source_images
list_storyboard_generation_queue
list_studio_docs
list_styles
list_video_workflows
log_image_prompt
lookup_character_identity
move_delivery_media
open_delivery_in_explorer
plan_image_edit
plan_scene_sequence
plan_storyboard_scene
plan_wan2gp_job
plan_wan_beat
polish_wan_best
polish_wan_video
read_studio_doc
recommend_polish
recycle_delivery_media
refine_image_forge
register_blender_control_maps
release_gpu_lock
reload_catalog
rename_delivery_media
resolve_character_loras
resolve_nsfw_scene_loras
resolve_style_lane
resolve_wan_action_loras
rewrite_chapter_phonetic
scan_models
search_studio_docs
setup_controlnet
setup_face_detail
setup_image_editing
setup_ip_adapter
setup_pose_control
splice_crossfade_loop
splice_pingpong
splice_pose_matched_loop
suggest_asset_name
switch_stills_backend
sync_checkpoint_architectures
unload_nari_for_gpu
update_project_context
upscale_video_local
view_delivery_image
view_delivery_video_frame
```

## Related public repos

- Heat / GPU status overlay (desk widget): [comfybox-heat-monitor](https://github.com/Jamescd1980/comfybox-heat-monitor) — includes CreateBrain placement (`iGPU` vs discrete GPU) on `/status`
