"""SS04-1 cum pour — quality MoE; opaque white creampie onto upside-down face/mouth.

Hero: thick white cum pouring onto face (jack-o upside-down).
Not an insertion hero. Skip Doggy Sex / Lightning.

T1 (rejected): female_orgasm 0.75 + pouring/pulsating → read as pee/squirt.
T2: no orgasm LoRA; opaque white cum pos + pee/urine neg — good motion, fluid color soft.
T3 (rejected): face-lock prompt + amp 0.35 → nothing happens (Recycle Bin).
T4: CloseUpFacialCum HIGH/LOW @0.70 + eyes closed + massive drip/coat; amp ~0.42.
    No orgasm (pee risk). No face essay / face_naturalizer (killed T3 motion).
    User: not bad but cum reads off-screen/aerial + coats chest not face; ~2.8s rushed.
T5: Chase T2 fluid + nearly frozen face → no cum (face-lock killed pour). Recycled.
T6: Hard on T2 fluid stack. No FacialCum / orgasm. amp 0.42 / 64f (~4s).
    Pos: T2 opaque pour + short "from her pussy" source clause + light eyes slowly close.
    Do NOT stack face nearly still / moving-face neg (killed T5 pour). Short pee neg only.
    User: almost perfect — stutter ~1s; cum landed floor behind head not face coat.
T7: Keep T6 opaque pussy overflow. FacialCum LOW only @0.50 (NO HIGH — T4 HIGH+LOW@0.7
    aerial). Strong face-coat path pussy→face. One motion family (overflow/drip onto face).
    Optional light cock pulsing clause (cock visible; not hero). amp 0.42 / 64f quality.
    Neg: pee + cum on floor / cum behind her head. Leave T6+T2 for A/B.
    User: funniest / spot on motion+path+face coat — fluid did NOT look like cum.
T8: Keep T7 motion/path/face-coat + FacialCum LOW @0.50 + amp 0.42 / 64f. Fix LOOK only:
    sticky thick white semen / milky opaque cum / creamy white jizz / sperm / real cum.
    Neg ≤6: urine, pee, yellow liquid, clear watery fluid, slime, mucus. Leave T7 A/B.
    Optional LOW→0.55 only if still not white (start 0.50).
    User: Miracle Whip / frosting — dairy stack + FacialCum overcooked opacity.
T9: Lean BJ_extra language. NO FacialCum. T7 path/amp/64f. Few strong tokens only
    (cum shot, sticky cum, thick white cum). No milky/creamy/jizz/sperm essay.
    Neg: urine, pee, yellow liquid, cream, frosting. Leave T7/T8 A/B.
    User: steaming hot white water (not MW; watery melt).
T10: Research fix. Viscosity without dairy/white stack: semen, sticky cum, cumshot.
    FacialCum HIGH+LOW correctly paired @0.40 (not LOW-only; not @0.55 frosting).
    Neg short: water/steam/watery/spray/transparent/milk. amp 0.40 / 64f quality.
    No orgasm / Lightning. Leave T7/T8/T9 A/B.
    User: look perfect; need more cum volume + a little motion (esp. penis).
T11: Keep T10 look stack (FacialCum H+L @0.40, viscosity tokens, short water neg).
    Volume clause + unlock body: amp 0.52; cock pulsing/throbbing + hips shifting.
    Drop steady view (was freezing). eyes slowly closing OK soft. Leave T10 A/B.
    User: more motion but honey look + cum hit breast (not face coat).
T12: Lean T10 look + mild motion. VERY short pos (sticky/cumshot/lots on face +
    pussy overflow). Neg minimal honey,water. FacialCum H+L @0.35 (below T10 0.40).
    Amp ~0.45. Optional start SS04-1_cumface.png (opaque white already on face).
    No orgasm/Lightning/eyes/hips essays. Leave T10/T11 A/B.
T13: Forge SS04-1_opaque.png (milky white at contact) + semen/sticky/cumshot +
    face-coat volume. FacialCum H+L @0.40, amp 0.42 / 64f quality. Neg honey/amber/
    transparent/water/steam. Leave T10–T12. User: keeper base / story match.
T13b: Tipout still (LF2I penis-only from T13 LF) → one-verb facial cumshot.
    FacialCum H+L @0.40, amp ~0.42 / 64f quality. Lean pos sticky/cumshot/face.
    No overflow essay / Lightning / orgasm. Leave T13.

Usage:
  py -3 run_ss04_1_cum.py V2_T13
  py -3 run_ss04_1_cum.py V2_T13b
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "general"))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio import engine as engine_mod  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

from recycle_path import recycle  # noqa: E402

PACK = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\scene_packs\Frieren Saloon"
)
OUT_DIR = Path(r"D:\ComfyBox Images and Videos\Video\Frieren\Saloon")
DIAG_ROOT = ROOT / "outputs" / "saloon_diag_frames" / "ss04_1_cum"

# Short neg only — long essays hurt Wan MoE. Rely on opaque-white pos.
NEG_CUM_POUR = "urine, pee, yellow liquid, clear watery fluid"

ORGASM_LORAS = [
    {
        "id": "orgasm_i2v_high",
        "file": "Wan22-I2V-Orgasm-HIGH-14B.safetensors",
        "weight": 0.75,
        "branch": "high",
    },
    {
        "id": "orgasm_i2v_low",
        "file": "Wan22-I2V-Orgasm-LOW-14B.safetensors",
        "weight": 0.75,
        "branch": "low",
    },
]

ORGASM_LORAS_SOFT = [
    {
        "id": "orgasm_i2v_high",
        "file": "Wan22-I2V-Orgasm-HIGH-14B.safetensors",
        "weight": 0.5,
        "branch": "high",
    },
    {
        "id": "orgasm_i2v_low",
        "file": "Wan22-I2V-Orgasm-LOW-14B.safetensors",
        "weight": 0.5,
        "branch": "low",
    },
]

# Local HIGH+LOW pair (not in MCP download_wan_video_loras catalog).
# CivitAI Close-Up Facial Cum v1.0 — already on comfybox Lora/.
FACIAL_CUM_LORAS = [
    {
        "id": "facial_cum_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 0.70,
        "branch": "high",
    },
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.70,
        "branch": "low",
    },
]

# Soft FacialCum if opacity needs help without full aerial bias (T5 skips; keep for T6).
FACIAL_CUM_LORAS_SOFT = [
    {
        "id": "facial_cum_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 0.48,
        "branch": "high",
    },
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.48,
        "branch": "low",
    },
]

# T7 experiment: LOW only @0.50 — face-landing detail without HIGH aerial bias.
FACIAL_CUM_LOW_ONLY = [
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.50,
        "branch": "low",
    },
]

# T8 escalate: same LOW-only, +0.05 if look still clear/mucus after prompt fix.
FACIAL_CUM_LOW_055 = [
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.55,
        "branch": "low",
    },
]

# T10: correct HIGH+LOW pair at low weight — opacity without frosting/aerial @0.7.
FACIAL_CUM_LORAS_040 = [
    {
        "id": "facial_cum_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 0.40,
        "branch": "high",
    },
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.40,
        "branch": "low",
    },
]

POS_OPAQUE_CUM = (
    "nsfw, from below, upside-down, "
    "thick white cum, opaque white semen, creampie, "
    "cum overflowing from her pussy, "
    "heavy ropes of white cum dripping onto her face and into her mouth, "
    "cum pulses of thick opaque semen pouring down, steady view"
)

POS_T4_DRIP_COAT = (
    "nsfw, from below, upside-down, sticky cum, "
    "thick white cum, opaque white semen, milky creampie overflow, "
    "she closes her eyes as massive amount of cum drips down, "
    "heavy ropes of opaque white cum coating her face, "
    "cum dripping onto her face, steady view"
)

# T2 fluid energy + source lock + face nearly frozen (T3 amp/face-lock was too hard @41f).
POS_T5_PUSSY_TO_FACE = (
    "nsfw, from below, upside-down, "
    "thick white cum, opaque white semen, creampie, "
    "cum overflowing from her pussy, "
    "heavy ropes of white cum dripping from her pussy onto her face and into her mouth, "
    "cum pulses of thick opaque semen pouring down, "
    "face nearly still, eyes slowly closing, soft lips barely moving, steady view"
)

NEG_T5 = "urine, pee, yellow liquid, moving face, talking"

# T2 energy + pussy source clause; light eyes only (no face freeze).
POS_T6_PUSSY_POUR = (
    "nsfw, from below, upside-down, "
    "thick white cum, opaque white semen, creampie, "
    "cum overflowing from her pussy, "
    "heavy ropes of white cum dripping from her pussy onto her face and into her mouth, "
    "cum pulses of thick opaque semen pouring down, "
    "eyes slowly closing, steady view"
)

NEG_T6 = "urine, pee, yellow liquid"

# T6 opaque overflow + strong face coat path; one drip/overflow family (anti-stutter).
# Light cock pulse clause only — cock visible in still, not the hero.
POS_T7_FACE_COAT = (
    "nsfw, from below, upside-down, "
    "thick white cum, opaque white semen, creampie, "
    "cum overflowing from her pussy, "
    "heavy ropes of white cum dripping from her pussy down onto her face, "
    "covering her face, cum on her face, face coated in thick white cum, "
    "cock pulsing as cum overflows from her pussy, "
    "eyes slowly closing, steady view"
)

NEG_T7 = "urine, pee, yellow liquid, cum on floor, cum behind her head"

# T8: same T7 path/motion; double down on opaque white semen LOOK (no new verbs/face-lock).
POS_T8_CUM_LOOK = (
    "nsfw, from below, upside-down, "
    "sticky thick white semen, milky opaque cum, creamy white jizz, sperm, "
    "looking like real cum, creampie, "
    "cum overflowing from her pussy, "
    "heavy ropes of sticky thick white semen dripping from her pussy down onto her face, "
    "covering her face, cum on her face, face coated in milky opaque cum, "
    "cock pulsing as cum overflows from her pussy, "
    "eyes slowly closing, steady view"
)

NEG_T8 = "urine, pee, yellow liquid, clear watery fluid, slime, mucus"

# T9: BJ_extra lean tokens + T7 pussy→face path. No FacialCum / dairy stack.
POS_T9_LEAN = (
    "nsfw, from below, upside-down, "
    "cum shot, sticky cum, thick white cum, "
    "cum overflowing from her pussy onto her face, "
    "ropes of cum drip onto her face, "
    "eyes slowly closing, steady view"
)

NEG_T9 = "urine, pee, yellow liquid, cream, frosting"

# T10: viscosity tokens (research) + T7 path; avoid white/dairy/cream stack that → water or MW.
POS_T10_VISCOSITY = (
    "nsfw, from below, upside-down, "
    "semen, sticky cum, cumshot, "
    "cum overflowing from her pussy onto her face, "
    "sticky cum drips onto her face, "
    "eyes slowly closing, steady view"
)

NEG_T10 = "water, steam, watery, spray, transparent, milk"

# T11: T10 look + volume + real body/penis motion (T10 frozen; amp 0.40 + steady view).
POS_T11_VOLUME_MOTION = (
    "nsfw, from below, upside-down, "
    "semen, sticky cum, cumshot, "
    "lots of cum, heavy cum flow, more cum pouring, "
    "cock pulsing and throbbing, hips shifting slightly, "
    "cum overflowing from her pussy onto her face, "
    "sticky cum drips onto her face, "
    "eyes slowly closing"
)

NEG_T11 = NEG_T10

# T12: lean T10 look + mild motion; face-coat volume; kill honey; no hips/eyes essay.
POS_T12_LEAN = (
    "nsfw, upside-down, sticky cum, cumshot, "
    "lots of cum covering her face, "
    "cum overflowing from her pussy onto her face"
)

NEG_T12 = "honey, water"

FACIAL_CUM_LORAS_035 = [
    {
        "id": "facial_cum_high",
        "file": "CloseUpFacialCum-v10_High.safetensors",
        "weight": 0.35,
        "branch": "high",
    },
    {
        "id": "facial_cum_low",
        "file": "CloseUpFacialCum-v10_Low.safetensors",
        "weight": 0.35,
        "branch": "low",
    },
]

BEATS = {
    "V2_T1": {
        "id": "SS04_1_v2_T1",
        "hypothesis": (
            "SS04-1 upside-down jack-o. Hero = pulsating + tremendous cum pouring "
            "from pussy onto face/mouth. female_orgasm HIGH/LOW 0.75, amp 0.45, "
            "45f quality. Not Doggy Sex; insertion incidental."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": (
            "nsfw, She is having an orgasm, from below, "
            "tremendous amount of thick white cum pulsing and pouring out of her pussy, "
            "cum streams down onto her face and into her open mouth, "
            "pulsating creampie overflow, steady view"
        ),
        "neg": NEG_CUM_POUR,
        "loras": ORGASM_LORAS,
        "amp": 0.45,
        "frames": 45,
    },
    "V2_T2": {
        "id": "SS04_1_v2_T2",
        "hypothesis": (
            "Retry after T1 pee-read. No female_orgasm. Opaque thick white cum / "
            "creampie overflow onto face+mouth. amp 0.42, 43f quality. "
            "SHORT neg only (urine/pee/yellow/clear watery)."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_OPAQUE_CUM,
        "neg": NEG_CUM_POUR,
        "loras": [],
        "amp": 0.42,
        "frames": 43,
        "short_neg": True,
    },
    "V2_T2b": {
        "id": "SS04_1_v2_T2b",
        "hypothesis": (
            "If T2 static: orgasm HIGH/LOW @0.5 + stronger opaque white cum pos. "
            "amp 0.42, 43f quality. SHORT pee neg kept."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": (
            POS_OPAQUE_CUM
            + ", heavy thick white creampie ropes pulsing out, milky opaque semen"
        ),
        "neg": NEG_CUM_POUR,
        "loras": ORGASM_LORAS_SOFT,
        "amp": 0.42,
        "frames": 43,
        "short_neg": True,
    },
    "V2_T3": {
        "id": "SS04_1_v2_T3",
        "hypothesis": (
            "REJECTED: face nearly still + amp 0.35 → no motion. Recycled."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": (
            "nsfw, from below, upside down, thick white cum coating her face, "
            "heavy opaque white semen covering her face, cum dripping onto her face, "
            "face nearly still, closed mouth or soft lips barely moving, steady view"
        ),
        "neg": "urine, pee, yellow liquid, talking, chewing, extreme facial expression",
        "loras": [],
        "amp": 0.35,
        "frames": 41,
        "short_neg": True,
    },
    "V2_T4": {
        "id": "SS04_1_v2_T4",
        "hypothesis": (
            "CloseUpFacialCum HIGH/LOW @0.70 for opaque white ropes. Keep T2 amp 0.42 "
            "for drip motion. Eyes-closed brief only (no face lock / face_naturalizer). "
            "No female_orgasm (pee). SHORT pee neg. 45f quality."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T4_DRIP_COAT,
        "neg": NEG_CUM_POUR,
        "loras": FACIAL_CUM_LORAS,
        "amp": 0.42,
        "frames": 45,
        "short_neg": True,
    },
    "V2_T5": {
        "id": "SS04_1_v2_T5",
        "hypothesis": (
            "User: T2 cum path/volume was good; fail was face moving + face quality trash. "
            "T4 FacialCum aerial/chest fail. Aim = T2 fluid (opaque white pussy overflow "
            "dripping/pouring onto face) + face nearly still (eyes slowly close). "
            "No FacialCum. amp 0.38 face-lock but 64f (~4s) so motion breathes. "
            "Neg: urine/pee/yellow + moving face/talking. Keep T2+T4 A/B."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T5_PUSSY_TO_FACE,
        "neg": NEG_T5,
        "loras": [],
        "amp": 0.38,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T6": {
        "id": "SS04_1_v2_T6",
        "hypothesis": (
            "Autopsy: T2 cum OK; T3 face-lock static; T4 FacialCum aerial/chest; "
            "T5 face-lock+moving-face-neg killed pour. T6 = T2 stack hard: no LoRA, "
            "amp 0.42, 64f (~4s), opaque pussy-to-face pour + light eyes slowly closing "
            "only. Neg urine/pee/yellow only. Accept mild face motion for fluid."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T6_PUSSY_POUR,
        "neg": NEG_T6,
        "loras": [],
        "amp": 0.42,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T7": {
        "id": "SS04_1_v2_T7",
        "hypothesis": (
            "T6 almost perfect: stutter ~1s + cum poured onto floor behind head. "
            "T7 = T6 opaque pussy overflow + strong face-coat language "
            "(covering her face / cum on her face / face coated) + path from pussy "
            "down onto face. CloseUpFacialCum LOW ONLY @0.50 (no HIGH — T4 HIGH+LOW "
            "@0.7 caused aerial). One motion family overflow/drip onto face; "
            "light cock pulsing clause (visible, not hero). amp 0.42 / 64f quality. "
            "Neg pee + cum on floor / cum behind her head. Leave T6+T2 A/B."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T7_FACE_COAT,
        "neg": NEG_T7,
        "loras": FACIAL_CUM_LOW_ONLY,
        "amp": 0.42,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T8": {
        "id": "SS04_1_v2_T8",
        "hypothesis": (
            "T7 motion/path/face coat loved; fluid look wrong (not cum). T8 keeps T7 "
            "path/amp/64f + LOOK stack; first pass LOW@0.50 still read translucent/mucus "
            "-> escalate FacialCum LOW only @0.55 (no HIGH). sticky thick white semen, "
            "milky opaque cum, creamy white jizz, sperm, looking like real cum. "
            "Neg <=6 pee/clear/slime. Leave T7 A/B."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T8_CUM_LOOK,
        "neg": NEG_T8,
        "loras": FACIAL_CUM_LOW_055,
        "amp": 0.42,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T9": {
        "id": "SS04_1_v2_T9",
        "hypothesis": (
            "Miracle Whip autopsy: T8 dairy stack (milky/creamy/jizz/sperm) + FacialCum "
            "LOW@0.55 made frosting paste. BJ_extra that read as real cum used lean "
            "'Facial, cum shot, sticky cum' + shoot motion - not cream adjectives. "
            "T9 = T7 path/amp/64f quality, NO FacialCum, lean pos only, short neg "
            "incl. cream/frosting. Leave T7/T8 A/B."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T9_LEAN,
        "neg": NEG_T9,
        "loras": [],
        "amp": 0.42,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T10": {
        "id": "SS04_1_v2_T10",
        "hypothesis": (
            "T9 watery steam autopsy: lean 'thick white cum' + no LoRA melted to hot "
            "white water/spray. Research: viscosity (sticky/semen/cumshot) not white/"
            "dairy; HIGH+LOW FacialCum paired (high=dynamics, low=appearance) at 0.40; "
            "neg water/steam/spray/milk short; amp 0.40 vs spray melt. quality MoE, "
            "no Lightning/orgasm. Leave T7/T8/T9 A/B."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T10_VISCOSITY,
        "neg": NEG_T10,
        "loras": FACIAL_CUM_LORAS_040,
        "amp": 0.40,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T11": {
        "id": "SS04_1_v2_T11",
        "hypothesis": (
            "T10 look perfect but body/penis frozen (only cum moved). Keep FacialCum "
            "HIGH+LOW @0.40 + viscosity + short water/steam neg. Volume clause + active "
            "verbs (cock pulsing and throbbing, hips shifting slightly, cum overflowing). "
            "Amp 0.52 motion budget; drop steady view. quality MoE 64f. Leave T10."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T11_VOLUME_MOTION,
        "neg": NEG_T11,
        "loras": FACIAL_CUM_LORAS_040,
        "amp": 0.52,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T12": {
        "id": "SS04_1_v2_T12",
        "hypothesis": (
            "T11 honey + breast aim after amp 0.52 + hips/cock verbs. T12 = lean T10 "
            "look + mild motion: VERY short pos (sticky/cumshot/lots covering face + "
            "pussy overflow), neg honey,water only, FacialCum H+L @0.35, amp 0.45, "
            "64f quality. Start SS04-1.png (cumface still prep skipped — paint/inpaint "
            "missed face). No orgasm/Lightning. Leave T10/T11."
        ),
        "image": PACK / "SS04-1.png",
        "prompt": POS_T12_LEAN,
        "neg": NEG_T12,
        "loras": FACIAL_CUM_LORAS_035,
        "amp": 0.45,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T13": {
        "id": "SS04_1_v2_T13",
        "hypothesis": (
            "T12 honey from amber start still. T13 = Forge-prepped SS04-1_opaque.png "
            "(flat milky white at contact) + T10 viscosity + face-coat volume. "
            "FacialCum HIGH+LOW @0.40, amp 0.42 / 64f quality MoE. Neg honey/amber/"
            "transparent/water/steam. No orgasm/Lightning. Leave T10–T12."
        ),
        "image": PACK / "SS04-1_opaque.png",
        "prompt": (
            "nsfw, upside-down, semen, sticky cum, cumshot, "
            "lots of cum covering her face, "
            "cum overflowing from her pussy onto her face"
        ),
        "neg": "honey, amber, transparent, water, steam",
        "loras": FACIAL_CUM_LORAS_040,
        "amp": 0.42,
        "frames": 64,
        "short_neg": True,
    },
    "V2_T13b": {
        "id": "SS04_1_v2_T13b_facial",
        "hypothesis": (
            "T13 keeper base. Tipout still (hard-mask LF2I penis-only from T13 LF) + "
            "ONE verb facial cumshot / ropes onto face. FacialCum HIGH+LOW @0.40, "
            "amp 0.42 / 64f quality MoE. Lean pos. Neg honey/water/transparent. "
            "No overflow essay / Lightning / orgasm. Leave T13; no auto-concat."
        ),
        "image": OUT_DIR / "SS04_1_T13_tipout.png",
        "prompt": "nsfw, sticky cum, cumshot, cum on her face",
        "neg": "honey, water, transparent",
        "loras": FACIAL_CUM_LORAS_040,
        "amp": 0.42,
        "frames": 64,
        "short_neg": True,
    },
}


def extract_frames(video: Path, diag_dir: Path, fps: float = 16.0) -> dict[str, Path]:
    diag_dir.mkdir(parents=True, exist_ok=True)
    dur_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video),
    ]
    try:
        dur = float(subprocess.check_output(dur_cmd, text=True).strip())
    except Exception:
        dur = 45 / fps
    probes = {"f0": 0.0, "mid": dur / 2, "last": max(0.0, dur - (1 / fps))}
    out: dict[str, Path] = {}
    for label, t in probes.items():
        dest = diag_dir / f"{video.stem}_{label}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(dest),
        ]
        subprocess.run(cmd, capture_output=True, check=False)
        if dest.is_file():
            out[label] = dest
    return out


def run_try(engine: GenerationEngine, beat: dict) -> dict:
    start = Path(beat["image"])
    dest = OUT_DIR / f"{beat['id']}.mp4"
    if not start.is_file():
        return {"ok": False, "id": beat["id"], "error": f"missing {start}"}

    print(
        f"===== I2V {beat['id']} quality amp={beat['amp']} frames={beat['frames']} =====",
        flush=True,
    )
    print("hypothesis:", beat.get("hypothesis", ""), flush=True)
    print("image", start, flush=True)
    print("prompt:", beat["prompt"], flush=True)
    print(
        "loras HIGH/LOW:",
        [(x["file"], x["weight"], x["branch"]) for x in beat["loras"]],
        flush=True,
    )

    # Engine auto-appends ANATOMY_NEGATIVE_HINT (imported into engine_mod).
    # Empty string is always "in" the prompt → append skipped; keep 4 short terms.
    prev_anat_neg = engine_mod.ANATOMY_NEGATIVE_HINT
    if beat.get("short_neg"):
        engine_mod.ANATOMY_NEGATIVE_HINT = ""
    try:
        result = engine.generate_video(
            prompt=beat["prompt"],
            mode="i2v",
            negative_prompt=beat["neg"],
            workflow_id="i2v",
            content_rating="open",
            image_path=str(start),
            num_frames=int(beat["frames"]),
            frame_rate=16.0,
            loras=beat["loras"],
            moe_preset="quality",
            smooth_motion=False,
            motion_amplitude=float(beat["amp"]),
        )
    finally:
        engine_mod.ANATOMY_NEGATIVE_HINT = prev_anat_neg

    saved = result.get("saved_files") or []
    if isinstance(saved, str):
        saved = [saved]

    promoted = None
    for p in saved:
        src = Path(str(p))
        if src.is_file() and src.suffix.lower() == ".mp4":
            if dest.is_file():
                recycle(dest)
            shutil.move(str(src), str(dest))
            promoted = dest
            break

    frames: dict[str, str] = {}
    if promoted:
        diag = DIAG_ROOT / beat["id"]
        extracted = extract_frames(promoted, diag)
        frames = {k: str(v) for k, v in extracted.items()}

    summary = {
        "ok": bool(promoted),
        "id": beat["id"],
        "hypothesis": beat.get("hypothesis"),
        "image": str(start),
        "path": str(promoted) if promoted else None,
        "preset": (result.get("moe") or {}).get("preset"),
        "motion_amplitude": beat["amp"],
        "frames": beat["frames"],
        "loras": beat["loras"],
        "prompt": beat["prompt"],
        "negative": beat["neg"],
        "diag_frames": frames,
        "result_ok": result.get("ok"),
        "error": result.get("error") or result.get("message"),
    }
    out_json = ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    beat_key = sys.argv[1] if len(sys.argv) > 1 else "V2_T1"
    if beat_key not in BEATS:
        print(f"unknown beat {beat_key}; known: {list(BEATS)}", flush=True)
        return 2
    beat = BEATS[beat_key]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    engine = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    summary = run_try(engine, beat)
    print("DONE", ROOT / "outputs" / f"saloon_{beat['id']}_i2v.json", flush=True)
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
