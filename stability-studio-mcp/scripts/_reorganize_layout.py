#!/usr/bin/env python3
"""One-shot: move NSFW vs general scripts into scripts/nsfw and scripts/general."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NSFW = ROOT / "nsfw"
GENERAL = ROOT / "general"

# Top-level .py files (not already in a subpackage) → nsfw or general
NSFW_NAMES = {
    "archive_bj_oral_ending.py",
    "download_bj_wan_loras.py",
    "download_bj_wan_loras_comfybox.py",
    "download_facial_cum_loras.py",
    "download_nsfw_image_loras.py",
    "download_orgasm_wan_lora.py",
    "download_penis_lora_hf.py",
    "download_penis_lora_taz.py",
    "find_bj_wan_loras.py",
    "frieren_sex_scenes_refine_kit.py",
    "frieren_tease_i2v_kit.py",
    "nari_recreate_stage1_soft.py",
    "package_frieren_sex_scene_packs.py",
    "restore_bj_ending.py",
    "run_bj_build_12s_and_wide.py",
    "run_bj_climax_cum_fix.py",
    "run_bj_facial_fidelity.py",
    "run_bj_facial_penislora.py",
    "run_bj_facial_retry.py",
    "run_bj_finish_creampie.py",
    "run_bj_i2v_14b.py",
    "run_bj_i2v_14b_shaftlock.py",
    "run_bj_pose_matched_25s.py",
    "run_bj_v2v_from_00005.py",
    "run_bj_wan22_closeup_square.py",
    "run_bj_wan22_loras.py",
    "run_frieren_sex_scenes_comfy_escalate.py",
    "run_frieren_sex_scenes_eyes_face_pass3.py",
    "run_frieren_sex_scenes_forge_fix_pass2.py",
    "run_frieren_sex_scenes_forge_refine.py",
    "run_frieren_tease_i2v_beats.py",
    "run_frieren_tease_wet_keys.py",
    "smoke_eric_s1b_wet.py",
}

GENERAL_TOP = {
    "build_handoff_zip.py",
    "build_native_i2v_14b_workflow.py",
    "check_asset_updates.py",
    "clean_outputs.py",
    "copy_rin_examples.py",
    "download_eye_water_loras.py",
    "download_moss_assets.py",
    "download_style_checkpoint.py",
    "download_style_recreation_loras.py",
    "download_wan22_lightning_loras.py",
    "download_wan2gp_i2v_assets.py",
    "download_wan_assets.py",
    "download_wan_video_loras.py",
    "dry_run_validation.py",
    "fix_legacy_hardcoded_paths.py",
    "patch_jan_i2v_guidance.py",
    "recycle_path.py",
    "run_frieren_s1a_eyes_boost.py",
    "run_style_recreation_stills.py",
    "run_style_recreation_stills_pass2.py",
    "run_style_recreation_stills_pass3.py",
    "run_style_recreation_stills_pass4.py",
    "run_wan2gp_hero.py",
    "search_style_eye_water_loras.py",
    "test_wan2gp_mcp_start.py",
}

NSFW_LOCAL_POST = {
    "polish_facial_test.py",
    "polish_jinah_final.py",
}

NSFW_DEV = {
    "_lookup_cum_loras.py",
    "find_nsfw_loras.py",
    "gen_naked_image.py",
    "verify_naked_checkpoint.py",
    "verify_nude_capability.py",
}


def move(src: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if src.resolve() == dest.resolve():
        return
    if dest.exists():
        print(f"skip exists {dest}")
        return
    print(f"{src.relative_to(ROOT)} -> {dest.relative_to(ROOT)}")
    shutil.move(str(src), str(dest))


def main() -> int:
    NSFW.mkdir(exist_ok=True)
    GENERAL.mkdir(exist_ok=True)
    (NSFW / "local_post").mkdir(exist_ok=True)
    (NSFW / "dev").mkdir(exist_ok=True)
    (GENERAL / "dev").mkdir(exist_ok=True)

    for name in NSFW_NAMES:
        p = ROOT / name
        if p.is_file():
            move(p, NSFW)
    for name in GENERAL_TOP:
        p = ROOT / name
        if p.is_file():
            move(p, GENERAL)

    # leftover top-level py (except helpers)
    skip = {"_bootstrap.py", "_reorganize_layout.py"}
    for p in ROOT.glob("*.py"):
        if p.name in skip:
            continue
        # default unknown to general
        move(p, GENERAL)

    lp = ROOT / "local_post"
    if lp.is_dir():
        for p in lp.glob("*.py"):
            if p.name in NSFW_LOCAL_POST:
                move(p, NSFW / "local_post")
            else:
                dest = GENERAL / "local_post"
                dest.mkdir(exist_ok=True)
                move(p, dest)
        # remove empty local_post
        if lp.is_dir() and not any(lp.iterdir()):
            lp.rmdir()

    dev = ROOT / "dev"
    if dev.is_dir():
        for p in dev.glob("*"):
            if not p.is_file():
                continue
            if p.name in NSFW_DEV or "nsfw" in p.name.lower() or "naked" in p.name.lower() or "nude" in p.name.lower() or "cum" in p.name.lower():
                move(p, NSFW / "dev")
            else:
                move(p, GENERAL / "dev")
        if dev.is_dir() and not any(dev.iterdir()):
            dev.rmdir()

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
