"""Frieren Tease Stage1–4 Wan I2V prompt kit (v3 — Wan 2.2 MoE 14B).

Language ban: never use cum / female cum for her.
Soft-body: hair bounce, breast bounce, ass-cheek jiggle when pose allows.
v3: workflow_id=i2v = Wan 2.2 I2V-A14B MoE HIGH+LOW (not Wan 2.1 single-UNET,
not i2v_5b). Climax beats use female_orgasm (HIGH+LOW pair).
"""

from __future__ import annotations

from pathlib import Path

TEASE_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\scene_packs\01_tease"
)
KEYS_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\tease_keys"
)
VIDEO_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren Tease")
CLIPS_DIR = VIDEO_DIR / "clips" / "v3_14b"

STAGE1 = TEASE_DIR / "01_Frieren_Stage1_forge.png"
STAGE2 = TEASE_DIR / "02_Frieren_Stage2_forge.png"
STAGE3 = TEASE_DIR / "03_Frieren_Stage3_forge.png"
STAGE4 = TEASE_DIR / "04_Frieren_Stage4_forge.png"

SOFT_BODY = (
    "bouncing breasts, breast jiggle, twin tails bouncing, hair sway, "
    "ass cheeks jiggling, soft body physics, natural bounce"
)

# Critical: kill rainbow melt / chromatic aberration / body morph from Wan 5B.
NEG = (
    "cum, semen, male ejaculation, text overlay, watermark, logo, "
    "stiff hair, frozen breasts, morphing hands, extra fingers, "
    "jittery, morphing, flickering, melting face, melting body, "
    "deformed face, deformed body, warping, liquid body, "
    "grabbing breast hard, yanking breast, dragging breast across body, "
    "pulling breast sideways, mauling breast, "
    "rainbow light, chromatic aberration, lens flare, prism light, "
    "green light leak, blue light leak, neon glow, iridescent artifacts, "
    "color fringing, holographic glare, oily skin bloom, "
    "bad anatomy, lowres, blurry"
)

# Subtle wet still (genital/fingers only) — avoid full-body oil sheen
WET_STILL_PROMPT = (
    "nb_frieren, frieren, nude elf girl, sitting on bed legs spread, "
    "fingering, wet pussy, light moisture on labia and fingers only, "
    "other hand squeezing breast, matte skin, natural skin, "
    "twin tails, red teardrop earrings, soft daylight bedroom, "
    "no lens flare, no rainbow lights, masterpiece, best quality, "
    "<lora:Frieren:0.8>"
)

COLLAPSE_STILL_PROMPT = (
    "nb_frieren, frieren, nude elf girl, after orgasm, lying back on bed pillows, "
    "legs still open, slightly wet pussy, matte skin, breathless, "
    "breasts settling, twin tails on pillows, soft daylight bedroom, "
    "no lens flare, masterpiece, best quality, <lora:Frieren:0.8>"
)

SQUIRT_STILL_PROMPT = (
    "nb_frieren, frieren, nude elf girl, sitting on bed legs spread, "
    "female ejaculation, clear fluid spray from pussy, soaked sheets, "
    "matte skin, orgasm face, twin tails, soft daylight bedroom, "
    "no lens flare, no rainbow, masterpiece, best quality, <lora:Frieren:0.8>"
)

BEATS = {
    # All Stage1 motion from clean Stage1 forge — wetness via light prompt only.
    "s1a_play": {
        "image": STAGE1,
        "prompt": (
            "slow fingering, fingers moving in and out, "
            "other hand softly squeezing her breast in place, lightly squeezing, "
            "gentle breast bounce, twin tails swaying, "
            "subtle hip movement, stable face, steady camera, natural daylight"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
    "s1b_wet": {
        "image": STAGE1,
        "prompt": (
            "more urgent fingering, wet pussy, glistening juices on fingers, "
            "other hand softly squeezing her breast, lightly squeezing in place, "
            "gentle breast bounce, hair sway, stable face and body, "
            "steady camera, natural daylight"
        ),
        "num_frames": 49,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
    "s1c_shudder": {
        "image": STAGE1,
        "prompt": (
            "she is having an orgasm, body shudders and shivers, thighs trembling, "
            "back arching, breasts shuddering, twin tails whipping, "
            "eyes half-closed in pleasure, fingers on clit, steady camera"
        ),
        "num_frames": 49,
        "workflow": "i2v",
        "loras": "orgasm_i2v_high,orgasm_i2v_low",
        "lora_bundle": "female_orgasm",
        "smooth_motion": False,
        "motion_amplitude": 1.15,
    },
    "s1d_squirt": {
        "image": STAGE1,
        "prompt": (
            "female ejaculation, squirting clear fluid from pussy, "
            "strong orgasm shudder, breasts bouncing, soaked sheets, steady camera"
        ),
        "num_frames": 33,
        "workflow": "i2v",
        "loras": "orgasm_i2v_high,orgasm_i2v_low",
        "lora_bundle": "female_orgasm",
        "smooth_motion": False,
        "motion_amplitude": 1.15,
    },
    "s1d_collapse": {
        "image": STAGE1,
        "prompt": (
            "after orgasm, body goes limp, falling back onto bed pillows, "
            "breasts settling, hair falling with her, legs still open, "
            "wet pussy glistening, steady camera"
        ),
        "num_frames": 49,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.1,
    },
    "s2_ride": {
        "image": STAGE2,
        "prompt": (
            "riding dildo, hip bounce, ass cheeks jiggling, breast bounce, "
            "twin tails bouncing, slow ride up and down, steady camera"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
    "s3_hand_dildo": {
        "image": STAGE3,
        "prompt": (
            "hand thrusting dildo, ass cheeks jiggling, hip movement, "
            "twin tails swaying, looking back over shoulder, steady camera"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
    "s4_dual_ride": {
        "image": STAGE4,
        "prompt": (
            "riding dildo, slow hip bounce, ass cheeks jiggling, breast bounce, "
            "twin tails bouncing, dual toys inserted, steady camera"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
}
