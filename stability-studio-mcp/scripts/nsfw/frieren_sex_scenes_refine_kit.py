"""Frieren Sex Scenes Forge refine kit — face QA refs + prompts.

Face quality bar (not identity):
  primary: recreate_003 (eyes/mouth/lips)
  secondary: recreate_007 (hair/skin lighting)
"""

from __future__ import annotations

from pathlib import Path

FACE_REF_PRIMARY = Path(
    r"D:\Test Images and Videos\_recreations\recreate_003_studio_agent_00009_.png"
)
FACE_REF_SECONDARY = Path(
    r"D:\Test Images and Videos\_recreations\recreate_007_studio_agent_00013_.png"
)

IMPORT_DIR = Path(r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens")
OUT_DIR = IMPORT_DIR / "_refined" / "pass1"
SCENE_PACKS_DIR = IMPORT_DIR / "_refined" / "scene_packs"

CHECKPOINT = "waijfu_alpha.safetensors"

# NSFW checkpoints expect explicit tags (blowjob, cock, pussy, doggystyle, …).
# Oral/insertion: ADetailer OFF + denoise ≤0.15, or keep original if contact breaks.
# Keep pose; bump face via ADetailer only on non-oral body-hero shots.
GLOBAL_PROMPT = (
    "nb_frieren, frieren, elf girl, long silver white hair, twin tails, "
    "pointed ears, red teardrop earrings, pale skin, nude, completely nude, "
    "masterpiece, best quality, highly detailed, sharp focus, "
    "detailed face, detailed eyes, anime illustration, <lora:Frieren:0.8>, "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.8>"
)

AD_PROMPT = (
    "nb_frieren, detailed face, beautiful detailed eyes, sharp iris, "
    "clear catchlights, detailed eyelashes, smooth skin, anime face, "
    "<lora:Frieren:0.75>, "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.85>"
)

NEGATIVE = (
    "lowres, bad anatomy, bad hands, extra fingers, missing fingers, "
    "mutated hands, deformed face, blurry face, soft face, plastic skin, "
    "shirt, collar, blouse, clothing, oversaturated, watermark, text, logo, "
    "worst quality, jpeg artifacts, star pupils, glowing eyes, wet skin overlay"
)

# Oral-specific (use with adetailer=False)
ORAL_POS_EXTRA = (
    "blowjob, fellatio, deepthroat, thick cock in mouth, lips wrapped around cock, "
    "cock filling mouth, oral sex"
)
ORAL_NEG_EXTRA = (
    "empty mouth, penis outside mouth, removed penis, small penis, tiny cock, "
    "shrinking penis, limp penis, floating penis, closed mouth"
)

# Pose-safe body denoise; ADetailer face denoise stays ~0.40 in forge_backend.
DENOISE = 0.32
STEPS = 28
CFG = 5.5

PILOT = "Frierenbj7.png"

SOURCES = [
    "Frieren_Stage1.png",
    "Frieren_Stage2.png",
    "Frieren_Stage3.png",
    "Frieren_Stage4.png",
    "Frieren_Cowgirl_Preinsert.png",
    "Frieren_Cowgirl1 (1).png",
    "Frieren_Missionary1.png",
    "Frieren_Doggystyle3.png",
    "Frierenbj4.png",
    "Frierenbj6.png",
    "Frierenbj7.png",
]

SCENE_PACKS = {
    "01_tease": [
        "Frieren_Stage1.png",
        "Frieren_Stage2.png",
        "Frieren_Stage3.png",
        "Frieren_Stage4.png",
    ],
    "02_cowgirl": [
        "Frieren_Cowgirl_Preinsert.png",
        "Frieren_Cowgirl1 (1).png",
    ],
    "03_missionary": [
        "Frieren_Missionary1.png",
    ],
    "04_rear_lookback": [
        "Frieren_Doggystyle3.png",
    ],
    "05_oral": [
        "Frierenbj4.png",
        "Frierenbj6.png",
        "Frierenbj7.png",
    ],
}
