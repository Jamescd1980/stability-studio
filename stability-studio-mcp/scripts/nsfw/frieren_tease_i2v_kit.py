"""Frieren Tease Stage1–4 Wan I2V prompt kit (v3 — Wan 2.2 MoE 14B).

Language ban: never use cum / female cum for her.
Soft-body: hair bounce, breast bounce, ass-cheek jiggle when pose allows.
v3: workflow_id=i2v = Wan 2.2 I2V-A14B MoE HIGH+LOW.

Delivery (one path, character-sorted):
  Video → D:\\ComfyBox Images and Videos\\Video\\Frieren\\
  Stills → User Import\\Frieren Sex Sceens\\_refined\\...
Fails → Windows Recycle Bin (do not leave quarantine trees around).
"""

from __future__ import annotations

from pathlib import Path

TEASE_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\scene_packs\01_tease"
)
KEYS_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\tease_keys"
)
# Canonical clip folder — character name only. No nested v3/_review/quarantine.
VIDEO_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
CLIPS_DIR = VIDEO_DIR

STAGE1 = TEASE_DIR / "01_Frieren_Stage1_forge.png"
STAGE2 = TEASE_DIR / "02_Frieren_Stage2_forge.png"
STAGE3 = TEASE_DIR / "03_Frieren_Stage3_forge.png"
STAGE4 = TEASE_DIR / "04_Frieren_Stage4_forge.png"

SOFT_BODY = (
    "bouncing breasts, breast jiggle, twin tails bouncing, hair sway, "
    "ass cheeks jiggling, soft body physics, natural bounce"
)

# Eyes + mouth discipline + dual-hand continuity.
# Soft eye life — do NOT push "lively/huge" or Wan grows doll eyes mid-clip.
EYE_LOCK = (
    "same eye size as start frame, keep Frieren eye shape, "
    "clear teal irises, subtle specular catchlights, sharp pupils, "
    "locked eye identity matching start frame"
)
MOUTH_OK = (
    "full plump lips, soft full mouth, lips lightly parted, "
    "soft breathing, quiet moan"
)
# Asymmetric pace: sensual breast hand vs faster fingering (Wan freezes the quieter hand).
# Keep fingering clearly faster than breast hand, but not frantic — post slowdown ~15–25% OK.
HANDS_BOTH = (
    "both hands keep moving the entire clip, never freeze either hand: "
    "left hand moderate rhythmic fingering, fingers thrusting in and out at a steady unhurried pace, "
    "right hand very slow sensual soft squeezing of her breast in place, gentle lingering knead"
)

NEG = (
    "cum, semen, male ejaculation, text overlay, watermark, logo, "
    "stiff hair, frozen breasts, frozen hands, one hand frozen, "
    "morphing hands, extra fingers, "
    "talking, speaking, mouthing words, lip sync, chewing, "
    "exaggerated mouth movement, wide open talking mouth, "
    "jittery, morphing, flickering, melting face, melting body, "
    "melting eyes, deformed eyes, crossed eyes, empty eyes, blank eyes, "
    "asymmetric eyes, blurry eyes, mushy pupils, "
    "oversized eyes, enlarged eyes, huge eyes, doll eyes, bug eyes, "
    "thin line mouth, tiny mouth, small mouth, lipless, "
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
    "s1a_play": {
        "image": STAGE1,  # forge master — not the overcooked eyes still
        "prompt": (
            f"{HANDS_BOTH}, "
            "gentle breast bounce, twin tails swaying, subtle hip movement, "
            f"{EYE_LOCK}, {MOUTH_OK}, "
            "steady camera, natural daylight"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        # Face naturalizer off — glassy eyes. No Illustrious eye LoRA on Wan path.
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
    # Prompt-tuned A/B from forge still (does not overwrite s1a_play keeper).
    "s1a_play_prompt": {
        "image": STAGE1,
        "prompt": (
            f"{HANDS_BOTH}, "
            "gentle breast bounce, twin tails swaying, subtle hip movement, "
            f"{EYE_LOCK}, {MOUTH_OK}, "
            "steady camera, natural daylight"
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
            f"{HANDS_BOTH}, "
            "wet pussy, glistening juices on fingers, "
            "gentle breast bounce, hair sway, "
            f"{EYE_LOCK}, {MOUTH_OK}, "
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
            "fingering hand keeps rubbing clit at a quick pace, "
            f"{EYE_LOCK}, eyes half-lidded in pleasure, {MOUTH_OK}, "
            "steady camera"
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
            "strong orgasm shudder, breasts bouncing, soaked sheets, "
            f"{EYE_LOCK}, {MOUTH_OK}, steady camera"
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
            "wet pussy glistening, "
            f"{EYE_LOCK}, {MOUTH_OK}, steady camera"
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
            "twin tails bouncing, slow ride up and down, "
            f"{EYE_LOCK}, {MOUTH_OK}, steady camera"
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
            "hand thrusting dildo continuously, ass cheeks jiggling, hip movement, "
            "twin tails swaying, looking back over shoulder, "
            f"{EYE_LOCK}, {MOUTH_OK}, steady camera"
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
            "twin tails bouncing, dual toys inserted, "
            f"{EYE_LOCK}, {MOUTH_OK}, steady camera"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 1.12,
    },
}
