"""Frieren Tease Wan I2V prompt kit (v3 — Wan 2.2 MoE 14B).

ABANDONED (2026-07-20): all Stage2/tease I2V outputs recycled.
Do not regenerate with current Wan stack — quality does not hold on ride/pump.
Forge stills in 01_tease remain for in-game / non-video use.
"""

from __future__ import annotations

from pathlib import Path

TEASE_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\scene_packs\01_tease"
)
GOLD_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\scene_packs\01_tease_gold"
)
GOLD_V2_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\scene_packs\01_tease_gold_v2"
)
KEYS_DIR = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\tease_keys"
)
VIDEO_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
CLIPS_DIR = VIDEO_DIR

STAGE2 = TEASE_DIR / "02_Frieren_Stage2_forge.png"
# Legacy path only — not used for video.
STAGE3 = TEASE_DIR / "03_Frieren_Stage3_forge.png"
STAGE1 = TEASE_DIR / "01_Frieren_Stage1_forge.png"
STAGE4 = GOLD_DIR / "04_Frieren_Stage4_forge_gold.png"
HANDS_BOTH = "both hands keep moving"
EYES_CLOSED_STILL = "eyes closed the entire clip"
FACE_MIN_CHANGE = "minimal face movement"
BODY_SOFT = "minimal body movement, soft breast bounce only"
SOFT_BODY = (
    "bouncing breasts, breast jiggle, twin tails bouncing, hair sway, "
    "ass cheeks jiggling, soft body physics, natural bounce"
)
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

STYLE_LOCK = (
    "same art style as start frame, same lighting as start frame, "
    "same color grading, keep render quality of start frame"
)
# Rear-view lock — do NOT mention eyes/mouth (that invents a face).
HEAD_FORWARD = (
    "head facing forward away from camera the entire clip, "
    "back of head only, face not visible, "
    "no looking over shoulder, no turning head, no face to camera"
)
EYE_LOCK = (
    "same eye size as start frame, keep Frieren eye shape, "
    "clear teal irises, subtle specular catchlights, sharp pupils, "
    "locked eye identity matching start frame"
)
MOUTH_OK = (
    "full plump lips, soft full mouth, lips lightly parted, "
    "soft breathing, quiet moan"
)

NEG = (
    "cum, semen, male ejaculation, text overlay, watermark, logo, "
    "cartoon, chibi, western cartoon, simplified shading, flat cel shading, "
    "cheap anime, low detail, plastic skin, oversaturated, "
    "looking over shoulder, looking at viewer, face to camera, "
    "turning head, profile face, inventing face, face morph, "
    "stiff hair, frozen breasts, frozen hands, one hand frozen, "
    "morphing hands, fused fingers, fingers melting together, extra fingers, "
    "talking, speaking, mouthing words, lip sync, chewing, "
    "exaggerated mouth movement, wide open talking mouth, "
    "jittery, morphing, flickering, melting face, melting body, "
    "melting eyes, deformed eyes, crossed eyes, empty eyes, blank eyes, "
    "asymmetric eyes, blurry eyes, mushy pupils, "
    "oversized eyes, enlarged eyes, huge eyes, doll eyes, bug eyes, "
    "ahegao, orgasm face morph, "
    "head shaking, head thrashing, body thrashing, jerky motion, "
    "violent shaking, back arching hard, hip thrusting hard, "
    "thin line mouth, tiny mouth, small mouth, lipless, "
    "bending dildo, floppy dildo, soft toy, rubber bend, "
    "legs thrashing, kicking legs, wild leg movement, "
    "picking up dildo, holding dildo in hand, "
    "single ponytail, hair style change, twin tails merging"
)

# Stage2 only: s2_dildo → s2_build → s2_pump → s2_slam. ONE beat at a time.
BEATS = {
    "s2_dildo": {
        # Clip 1 — keeper quality bar. Head forward = no invented face.
        "image": STAGE2,
        "prompt": (
            "nsfw, nude elf girl kneeling facing away, same pose as start frame, "
            f"{STYLE_LOCK}, {HEAD_FORWARD}, "
            "twin tails stay as two separate tails matching start frame, "
            "thick purple dildo standing upright on the rug under her crotch, "
            "dildo stays planted on the floor, never picked up, never held in hand, "
            "very slight slow hip bounce, soft breast bounce, "
            "twin tails swaying, hands stay on the floor matching start frame, "
            "legs and knees planted, no thrashing, "
            "steady camera, bright window backlight"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 0.75,
    },
    "s2_build": {
        # ~3s soft continue — forge still.
        "image": STAGE2,
        "prompt": (
            "nsfw, nude elf girl kneeling facing away, same pose as start frame, "
            f"{STYLE_LOCK}, {HEAD_FORWARD}, "
            "twin tails stay as two separate tails matching start frame, "
            "thick purple dildo standing upright on the rug under her crotch, "
            "dildo stays planted on the floor, never picked up, never held in hand, "
            "very slight slow hip bounce, soft breast bounce, "
            "twin tails swaying, hands stay on the floor matching start frame, "
            "legs and knees planted, no thrashing, "
            "steady camera, bright window backlight"
        ),
        "num_frames": 49,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 0.75,
    },
    "s2_pump": {
        # After approved s2_build — modest lift then settle (keeper amp). No "almost exits".
        "image": CLIPS_DIR / "s2_build_lastframe.png",
        "prompt": (
            "nsfw, nude elf girl kneeling facing away, same pose as start frame, "
            f"{STYLE_LOCK}, {HEAD_FORWARD}, "
            "twin tails stay as two separate tails matching start frame, "
            "thick purple dildo planted upright on the rug under her crotch, "
            "dildo stays fixed on the floor, never picked up, never held in hand, never bends, "
            "slow modest hip lift a little higher, then gently lowers back down, "
            "small vertical hip motion only, keep contact with the dildo, "
            "soft breast bounce, twin tails swaying, "
            "hands stay on the floor bracing, knees planted, no thrashing, "
            "steady camera, bright window backlight"
        ),
        "num_frames": 49,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 0.75,
    },
    "s2_slam": {
        # Later climax — only after pump is approved. Face may appear when head tilts back.
        "image": CLIPS_DIR / "s2_pump_lastframe.png",
        "prompt": (
            "nsfw, nude elf girl kneeling over a thick purple dildo planted on the rug, "
            f"{STYLE_LOCK}, "
            "dildo stays fixed upright on the floor the entire clip, never held in hand, "
            "she lowers her hips and sits down firmly onto the dildo, "
            "then stays fully seated without bouncing, "
            "tilts her head back looking upward, chin lifted, "
            "soft quiet moan, twin tails falling back, "
            "soft breast bounce then settle, "
            "hands stay on the floor bracing, no thrashing, "
            "steady camera, bright window backlight"
        ),
        "num_frames": 65,
        "workflow": "i2v",
        "loras": "",
        "smooth_motion": False,
        "motion_amplitude": 0.78,
    },
}

VIDEO_ALLOWED_BEATS = frozenset(BEATS)
VIDEO_ALLOWED_STAGES = (2,)
