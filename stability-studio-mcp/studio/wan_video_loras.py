"""Optional Wan 2.2 video LoRAs (motion, face, lighting, camera) — separate from base WORKFLOW_ASSETS.

MoE note: Wan 2.2 I2V-A14B uses HIGH + LOW experts. Action / distill LoRAs are usually
paired — put HIGH files on the high branch and LOW files on the low branch. Never dump
many singles onto one UNET. Typical stack: Lightning pair + 0–1 action pair (+ optional face).
"""

from __future__ import annotations

from typing import Any

from studio.wan_assets import FOLDER_MAP, _find_file, download_asset, model_dirs

HF_REPO = "wangkanai/wan22-fp16-i2v-loras"

# Curated I2V-friendly LoRAs (fp16, Wan 2.2). Download into Stability Matrix Lora/.
# branch: high | low | both — used by wan22 MoE stacking (ignored on single-UNET 5B inject).
WAN_VIDEO_LORAS: dict[str, dict[str, Any]] = {
    "lightning_i2v_high": {
        "id": "lightning_i2v_high",
        "filename": "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors",
        "folder": "loras",
        "repo": "lightx2v/Wan2.2-Distill-Loras",
        "path": "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors",
        "size_hint": "~300 MB",
        "default_weight": 0.7,
        "branch": "high",
        "workflows": ["i2v"],
        "purpose": "LightX2V distill HIGH — motion/structure backbone for Wan 2.2 MoE.",
    },
    "lightning_i2v_low": {
        "id": "lightning_i2v_low",
        "filename": "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors",
        "folder": "loras",
        "repo": "lightx2v/Wan2.2-Distill-Loras",
        "path": "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors",
        "size_hint": "~300 MB",
        "default_weight": 1.0,
        "branch": "low",
        "workflows": ["i2v"],
        "purpose": "LightX2V distill LOW — detail/stability half for Wan 2.2 MoE.",
    },
    "face_naturalizer": {
        "id": "face_naturalizer",
        "filename": "wan22-face-naturalizer.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-face-naturalizer.safetensors",
        "size_hint": "~586 MB",
        "default_weight": 0.65,
        "branch": "both",
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter", "i2v"],
        "purpose": "Face/eye stability on Wan 2.2 (use on MoE both branches; best eye tool we have).",
    },
    "light_volumetric": {
        "id": "light_volumetric",
        "filename": "wan22-light-volumetric.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-light-volumetric.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.5,
        "branch": "both",
        "workflows": ["i2v_5b", "i2v_5b_painter", "i2v", "t2v"],
        "purpose": "Volumetric god-rays / cinematic church lighting.",
    },
    "camera_steady": {
        "id": "camera_steady",
        "filename": "wan22-camera-rotation-rank16-v2.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-camera-rotation-rank16-v2.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.35,
        "branch": "both",
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Controlled orbit/rotation — use low weight for steady aisle dolly.",
    },
    "camera_arc": {
        "id": "camera_arc",
        "filename": "wan22-camera-arcshot-rank16-v2-high.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-camera-arcshot-rank16-v2-high.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.4,
        "branch": "high",
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Cinematic arc shot around subject.",
    },
    "action_wink": {
        "id": "action_wink",
        "filename": "wan22-action-wink-i2v-v1-low.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-action-wink-i2v-v1-low.safetensors",
        "size_hint": "~147 MB",
        "default_weight": 0.55,
        "branch": "low",
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Small gesture motion reference (not for walk cycles).",
    },
    # Female climax motion (Playtime_AI). Prefer prompt trigger: "She is having an orgasm."
    # Trained for Wan 2.2 I2V 14B HIGH/LOW — must stack as a pair on MoE i2v.
    "orgasm_i2v_high": {
        "id": "orgasm_i2v_high",
        "filename": "Wan22-I2V-Orgasm-HIGH-14B.safetensors",
        "folder": "loras",
        "repo": "iarcanar/wan22_template",
        "path": "Wan2.2 - I2V - Orgasm - HIGH 14B.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.75,
        "branch": "high",
        "pair_id": "orgasm_i2v_low",
        "workflows": ["i2v", "i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Orgasm shudder HIGH (motion). Trigger: She is having an orgasm.",
    },
    "orgasm_i2v_low": {
        "id": "orgasm_i2v_low",
        "filename": "Wan22-I2V-Orgasm-LOW-14B.safetensors",
        "folder": "loras",
        "repo": "iarcanar/wan22_template",
        "path": "Wan2.2 - I2V - Orgasm - LOW 14B.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.75,
        "branch": "low",
        "pair_id": "orgasm_i2v_high",
        "workflows": ["i2v"],
        "purpose": "Orgasm LoRA LOW (detail/stability) for Wan 2.2 MoE I2V.",
    },
    # CubeyAI WAN General NSFW — closest all-in-one sex anatomy pair (penis/vagina).
    # Trigger historically nsfwsks; prefer LOW ~0.4–0.6 for detail; light HIGH if needed.
    "general_nsfw_i2v_high": {
        "id": "general_nsfw_i2v_high",
        "filename": "NSFW-22-H-e8.safetensors",
        "folder": "loras",
        "repo": "CubeyAI/Wan2.2-General-NSFW",
        "path": "NSFW-22-H-e8.safetensors",
        "size_hint": "~586 MB",
        "default_weight": 0.45,
        "branch": "high",
        "pair_id": "general_nsfw_i2v_low",
        "workflows": ["i2v"],
        "purpose": "General NSFW HIGH (motion/structure). Trigger: nsfwsks.",
    },
    "general_nsfw_i2v_low": {
        "id": "general_nsfw_i2v_low",
        "filename": "NSFW-22-L-e8.safetensors",
        "folder": "loras",
        "repo": "CubeyAI/Wan2.2-General-NSFW",
        "path": "NSFW-22-L-e8.safetensors",
        "size_hint": "~586 MB",
        "default_weight": 0.5,
        "branch": "low",
        "pair_id": "general_nsfw_i2v_high",
        "workflows": ["i2v"],
        "purpose": "General NSFW LOW (anatomy/detail). Trigger: nsfwsks.",
    },
    # Taz PENISLORA — shaft/glans lock; helps keep toys/shafts rigid on I2V.
    "penis_i2v_high": {
        "id": "penis_i2v_high",
        "filename": "PENISLORA_wan22_i2v_high.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "PENISLORA_wan22_i2v_high.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.55,
        "branch": "high",
        "pair_id": "penis_i2v_low",
        "workflows": ["i2v"],
        "purpose": "Penis/shaft rigidity HIGH. Trigger: PENISLORA.",
    },
    "penis_i2v_low": {
        "id": "penis_i2v_low",
        "filename": "PENISLORA_wan22_i2v_low.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "PENISLORA_wan22_i2v_low.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.55,
        "branch": "low",
        "pair_id": "penis_i2v_high",
        "workflows": ["i2v"],
        "purpose": "Penis/shaft rigidity LOW. Trigger: PENISLORA.",
    },
    # --- Action pairs (on-disk / local-OK; empty repo = no HF download) ---
    # Oral insertion — proven BJ stack. MoE: HIGH motion + LOW detail.
    "oral_insertion_i2v_high": {
        "id": "oral_insertion_i2v_high",
        "filename": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.6,
        "branch": "high",
        "pair_id": "oral_insertion_i2v_low",
        "workflows": ["i2v"],
        "purpose": "Oral insertion HIGH (tip-in-mouth / bob). Pair required on MoE.",
    },
    "oral_insertion_i2v_low": {
        "id": "oral_insertion_i2v_low",
        "filename": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.6,
        "branch": "low",
        "pair_id": "oral_insertion_i2v_high",
        "workflows": ["i2v"],
        "purpose": "Oral insertion LOW. Pair with oral_insertion_i2v_high.",
    },
    # Ultimate DeepThroat K3NK — Elven Appetite / Pale Elf Rider BJ keepers (with oral_insertion).
    "ultimate_deepthroat_i2v_high": {
        "id": "ultimate_deepthroat_i2v_high",
        "filename": "wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.45,
        "branch": "high",
        "pair_id": "ultimate_deepthroat_i2v_low",
        "workflows": ["i2v"],
        "purpose": "Ultimate DeepThroat HIGH. Vertical bury/bob. Pair with oral_insertion for deepthroat keepers.",
    },
    "ultimate_deepthroat_i2v_low": {
        "id": "ultimate_deepthroat_i2v_low",
        "filename": "wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.45,
        "branch": "low",
        "pair_id": "ultimate_deepthroat_i2v_high",
        "workflows": ["i2v"],
        "purpose": "Ultimate DeepThroat LOW. Pair with ultimate_deepthroat_i2v_high.",
    },
    # Missionary Sex — already-in thrust (not tip→bury). playtime_ai mirrors.
    "missionary_sex_i2v_high": {
        "id": "missionary_sex_i2v_high",
        "filename": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.55,
        "branch": "high",
        "pair_id": "missionary_sex_i2v_low",
        "workflows": ["i2v"],
        "purpose": "Missionary Sex HIGH — already-in front-to-back thrusts. Wrong for tip-only stills.",
    },
    "missionary_sex_i2v_low": {
        "id": "missionary_sex_i2v_low",
        "filename": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.55,
        "branch": "low",
        "pair_id": "missionary_sex_i2v_high",
        "workflows": ["i2v"],
        "purpose": "Missionary Sex LOW. Pair with missionary_sex_i2v_high.",
    },
    # POV Missionary Insertion (The_Cook) — tip→bury / stay-buried.
    "pov_insertion_i2v_high": {
        "id": "pov_insertion_i2v_high",
        "filename": "wan2.2-i2v-high-pov-missionary-insertion-v1.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-high-pov-missionary-insertion-v1.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.6,
        "branch": "high",
        "pair_id": "pov_insertion_i2v_low",
        "workflows": ["i2v"],
        "purpose": "POV Missionary Insertion HIGH — tip→in / stay buried. Split weights OK (e.g. 0.35/1.0).",
    },
    "pov_insertion_i2v_low": {
        "id": "pov_insertion_i2v_low",
        "filename": "wan2.2-i2v-low-pov-missionary-insertion-v1.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-low-pov-missionary-insertion-v1.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.6,
        "branch": "low",
        "pair_id": "pov_insertion_i2v_high",
        "workflows": ["i2v"],
        "purpose": "POV Missionary Insertion LOW. Pair with pov_insertion_i2v_high.",
    },
    # Doggy Style Sex — rear pose family only (not Missionary Sex).
    "doggy_sex_i2v_high": {
        "id": "doggy_sex_i2v_high",
        "filename": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.55,
        "branch": "high",
        "pair_id": "doggy_sex_i2v_low",
        "workflows": ["i2v"],
        "purpose": "Doggy Style Sex HIGH. Trigger: they are having doggy style sex.",
    },
    "doggy_sex_i2v_low": {
        "id": "doggy_sex_i2v_low",
        "filename": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.55,
        "branch": "low",
        "pair_id": "doggy_sex_i2v_high",
        "workflows": ["i2v"],
        "purpose": "Doggy Style Sex LOW. Pair with doggy_sex_i2v_high.",
    },
    # CloseUp FacialCum — local-only facial shoot. HIGH=dynamics, LOW=appearance.
    "facial_cum_i2v_high": {
        "id": "facial_cum_i2v_high",
        "filename": "CloseUpFacialCum-v10_High.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "CloseUpFacialCum-v10_High.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.4,
        "branch": "high",
        "pair_id": "facial_cum_i2v_low",
        "workflows": ["i2v"],
        "purpose": "FacialCum HIGH (rope/dynamics). Facial shoot only; ~0.4 keepers. Local-only.",
    },
    "facial_cum_i2v_low": {
        "id": "facial_cum_i2v_low",
        "filename": "CloseUpFacialCum-v10_Low.safetensors",
        "folder": "loras",
        "repo": "",
        "path": "CloseUpFacialCum-v10_Low.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.4,
        "branch": "low",
        "pair_id": "facial_cum_i2v_high",
        "workflows": ["i2v"],
        "purpose": "FacialCum LOW (appearance). Never LOW-only for look. Local-only.",
    },
}

# Suggested bundles for agents / docs.
WAN_VIDEO_LORA_BUNDLES: dict[str, list[str]] = {
    "walk_cycle": ["face_naturalizer"],
    # NOTE: smooth_motion=true auto-picks this — face_naturalizer + camera_steady (not a motion smoother).
    "smooth_character": ["face_naturalizer", "camera_steady"],
    "cinematic_church": ["face_naturalizer", "light_volumetric"],
    "motion_boost": ["face_naturalizer", "light_volumetric", "camera_steady"],
    # Always both halves on MoE — never orgasm HIGH alone on i2v.
    "female_orgasm": ["orgasm_i2v_high", "orgasm_i2v_low"],
    "lightning_i2v": ["lightning_i2v_high", "lightning_i2v_low"],
    # face_lock = face_naturalizer only; can freeze micro-motion (drip/moan) if over-prompted still.
    "face_lock": ["face_naturalizer"],
    "orgasm_face": ["face_naturalizer", "orgasm_i2v_high", "orgasm_i2v_low"],
    "orgasm_lightning": [
        "lightning_i2v_high",
        "lightning_i2v_low",
        "orgasm_i2v_high",
        "orgasm_i2v_low",
    ],
    "general_nsfw": ["general_nsfw_i2v_high", "general_nsfw_i2v_low"],
    "general_nsfw_low_only": ["general_nsfw_i2v_low"],
    "penis_lock": ["penis_i2v_high", "penis_i2v_low"],
    "nsfw_penis": [
        "general_nsfw_i2v_high",
        "general_nsfw_i2v_low",
        "penis_i2v_high",
        "penis_i2v_low",
    ],
    "nsfw_lightning": [
        "lightning_i2v_high",
        "lightning_i2v_low",
        "general_nsfw_i2v_high",
        "general_nsfw_i2v_low",
    ],
    # Action pairs — one per keeper; quality MoE (no Lightning) unless draft.
    "oral_insertion": ["oral_insertion_i2v_high", "oral_insertion_i2v_low"],
    # Proven Elven Appetite / Pale Elf Rider deepthroat stack (oral + Ultimate DeepThroat).
    # Exception to one-action-pair rule — see LESSONS-WAN-I2V.md BJ recipe.
    "oral_deepthroat": [
        "oral_insertion_i2v_high",
        "oral_insertion_i2v_low",
        "ultimate_deepthroat_i2v_high",
        "ultimate_deepthroat_i2v_low",
    ],
    "ultimate_deepthroat": [
        "ultimate_deepthroat_i2v_high",
        "ultimate_deepthroat_i2v_low",
    ],
    "missionary_sex": ["missionary_sex_i2v_high", "missionary_sex_i2v_low"],
    "pov_insertion": ["pov_insertion_i2v_high", "pov_insertion_i2v_low"],
    "doggy_sex": ["doggy_sex_i2v_high", "doggy_sex_i2v_low"],
    "facial_cum": ["facial_cum_i2v_high", "facial_cum_i2v_low"],
}

# Scene → action-bundle hints for agents (first match wins). Used by suggest_wan_action_lora.
# Order matters: more specific beats before generic sex.
WAN_ACTION_LORA_SCENE_HINTS: list[tuple[str, tuple[str, ...]]] = [
    (
        "facial_cum",
        (
            "facial cum",
            "cum on face",
            "facial shoot",
            "bukkake",
            "rope of cum",
            "cumshot on face",
        ),
    ),
    (
        "oral_deepthroat",
        (
            "deepthroat",
            "deep throat",
            "throat",
            "bury in her mouth",
            "takes him deeper",
            "mouth slides down",
        ),
    ),
    (
        "oral_insertion",
        (
            "blowjob",
            "fellatio",
            "oral",
            "cock in mouth",
            "cock into her mouth",
            "lips wrapped",
            "head bob",
            "head slides down",
            "slides down the shaft",
            "tip in mouth",
            "sucking cock",
            "facefuck",
        ),
    ),
    (
        "doggy_sex",
        (
            "doggystyle",
            "doggy style",
            "doggy",
            "from behind",
            "rear entry",
            "prone bone",
            "on all fours",
        ),
    ),
    (
        "pov_insertion",
        (
            "tip to in",
            "tip→in",
            "pushes in and stays",
            "slowly pushes his cock into",
            "insertion",
            "burying",
            "stays buried",
            "tip at entrance",
        ),
    ),
    (
        "missionary_sex",
        (
            "missionary",
            "mating press",
            "already in",
            "thrusting",
            "front to back",
            "cowgirl",
            "vaginal penetration",
        ),
    ),
]


def suggest_wan_action_lora(
    prompt: str = "",
    *,
    beat_hint: str = "",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recommend one MoE action LoRA bundle from prompt/beat text + install check.

    Agents must call this (or check_wan_video_loras for a known bundle) *before*
    generate_video when the beat is NSFW sex/oral — do not hope the base model
    invents the motion.
    """
    text = f"{beat_hint}\n{prompt}".strip().lower()
    checklist = [
        "Identify beat type (oral / doggy / tip→in / already-in thrust / facial).",
        "Map to one action bundle (oral_insertion|doggy_sex|pov_insertion|missionary_sex|facial_cum).",
        "call check_wan_video_loras(lora_ids=<bundle ids>) or use this tool's ready flag.",
        "If missing: download_wan_video_loras(bundle=<id>) then re-check.",
        "Pass lora_bundle=<id> into generate_video (quality MoE; at most one action pair).",
        "Do not skip LoRAs and 'prompt hope' hard contact / bob / insertion motion.",
    ]

    matched_bundle = ""
    matched_on = ""
    if beat_hint.strip().lower() in WAN_VIDEO_LORA_BUNDLES:
        # Allow explicit bundle id as beat_hint
        bh = beat_hint.strip().lower()
        if bh in (
            "oral_insertion",
            "oral_deepthroat",
            "ultimate_deepthroat",
            "missionary_sex",
            "pov_insertion",
            "doggy_sex",
            "facial_cum",
        ):
            matched_bundle = bh
            matched_on = "beat_hint_bundle_id"
    if not matched_bundle and text:
        for bundle, needles in WAN_ACTION_LORA_SCENE_HINTS:
            for needle in needles:
                if needle in text:
                    matched_bundle = bundle
                    matched_on = needle
                    break
            if matched_bundle:
                break

    ids = list(WAN_VIDEO_LORA_BUNDLES.get(matched_bundle, [])) if matched_bundle else []
    status = check_wan_video_loras(cfg or {}, ids) if ids else {
        "installed": [],
        "missing": [],
        "ready": False,
    }
    purpose = ""
    if matched_bundle and ids:
        try:
            purpose = str(resolve_lora_entry(ids[0]).get("purpose") or "")
        except KeyError:
            purpose = ""

    return {
        "ok": True,
        "checklist": checklist,
        "prompt_excerpt": (prompt or "")[:160],
        "beat_hint": beat_hint or None,
        "recommended_bundle": matched_bundle or None,
        "matched_on": matched_on or None,
        "lora_ids": ids,
        "generate_video_args": (
            {"lora_bundle": matched_bundle, "moe_preset": "quality"}
            if matched_bundle
            else None
        ),
        "purpose": purpose or None,
        "ready": bool(status.get("ready")) if matched_bundle else False,
        "installed": status.get("installed") or [],
        "missing": status.get("missing") or [],
        "bundles_action": [
            "oral_insertion",
            "oral_deepthroat",
            "ultimate_deepthroat",
            "doggy_sex",
            "pov_insertion",
            "missionary_sex",
            "facial_cum",
        ],
        "note": (
            "Before every NSFW Wan I2V keeper: run resolve_wan_action_loras (or "
            "check_wan_video_loras) and pass lora_bundle when a match is ready. "
            "Stack limit: Lightning (draft only) + at most one action pair "
            "(exception: oral_deepthroat = oral_insertion + Ultimate DeepThroat)."
            if matched_bundle
            else (
                "No action bundle matched — if this is sex/oral/doggy/insert, set "
                "beat_hint=oral_insertion|oral_deepthroat|doggy_sex|pov_insertion|"
                "missionary_sex|facial_cum "
                "explicitly, then check/download before generate_video."
            )
        ),
    }

# Optional machine-local LoRAs (gitignored). Copy wan_video_loras_local.example.py → wan_video_loras_local.py
try:
    from studio.wan_video_loras_local import (  # type: ignore[import-not-found]
        LOCAL_WAN_VIDEO_LORA_BUNDLES,
        LOCAL_WAN_VIDEO_LORAS,
    )

    WAN_VIDEO_LORAS.update(LOCAL_WAN_VIDEO_LORAS)
    WAN_VIDEO_LORA_BUNDLES.update(LOCAL_WAN_VIDEO_LORA_BUNDLES)
except ImportError:
    pass

# Tuned defaults when generate_video(smooth_motion=true).
SMOOTH_MOTION_DEFAULTS: dict[str, Any] = {
    "motion_amplitude": 1.08,
    "frame_rate": 12.0,
    "sampler_steps": 28,
    "sampler_cfg": 5.0,
    "lora_bundle": "smooth_character",
    "extra_negative": "jittery, morphing, flickering, strobe, fast erratic motion, warping",
}


def apply_smooth_motion_preset(
    *,
    smooth_motion: bool,
    motion_amplitude: float,
    frame_rate: float | None,
    lora_bundle: str,
    lora_ids: list[str] | None,
    vram_gb: float | None = None,
) -> tuple[float, float | None, str, list[str] | None, dict[str, Any]]:
    """Return tuned motion/fps/lora settings for smoother Wan I2V/V2V."""
    applied: dict[str, Any] = {}
    if not smooth_motion:
        return motion_amplitude, frame_rate, lora_bundle, lora_ids, applied

    defaults = SMOOTH_MOTION_DEFAULTS
    if motion_amplitude >= 1.12:
        motion_amplitude = float(defaults["motion_amplitude"])
        applied["motion_amplitude"] = motion_amplitude
    if frame_rate is None:
        frame_rate = float(defaults["frame_rate"])
        applied["frame_rate"] = frame_rate
    # Dual Wan video LoRAs (~900 MB loaded) can OOM with PainterI2V on 16 GB GPUs.
    if not lora_bundle and not lora_ids:
        if vram_gb is not None and vram_gb <= 16:
            applied["lora_bundle_skipped"] = (
                f"{vram_gb:.0f}GB VRAM — using PainterI2V only (no Wan video LoRAs)"
            )
        else:
            lora_bundle = str(defaults["lora_bundle"])
            applied["lora_bundle"] = lora_bundle
    applied["sampler_steps"] = defaults["sampler_steps"]
    applied["sampler_cfg"] = defaults["sampler_cfg"]
    applied["extra_negative"] = defaults["extra_negative"]
    return motion_amplitude, frame_rate, lora_bundle, lora_ids, applied


def resolve_lora_entry(lora_id: str) -> dict[str, Any]:
    key = lora_id.strip().lower()
    if key in WAN_VIDEO_LORAS:
        return WAN_VIDEO_LORAS[key]
    for entry in WAN_VIDEO_LORAS.values():
        if entry["filename"].lower() == key or entry["filename"].lower() == f"{key}.safetensors":
            return entry
    raise KeyError(f"Unknown Wan video LoRA id: {lora_id!r}. Known: {list(WAN_VIDEO_LORAS)}")


def resolve_lora_list(
    lora_ids: list[str] | None = None,
    *,
    bundle: str = "",
    weights: dict[str, float] | None = None,
    auto_pair: bool = True,
) -> list[dict[str, Any]]:
    """Return [{file, weight, id, branch}, ...] for workflow injection."""
    ids: list[str] = []
    if bundle:
        ids.extend(WAN_VIDEO_LORA_BUNDLES.get(bundle.strip().lower(), []))
    if lora_ids:
        ids.extend(lora_ids)
    if not ids:
        return []

    if auto_pair:
        # If only one half of a HIGH/LOW pair is requested, add the mate for MoE.
        extras: list[str] = []
        for raw in list(ids):
            try:
                entry = resolve_lora_entry(raw)
            except KeyError:
                continue
            mate = entry.get("pair_id")
            if mate and mate not in {x.strip().lower() for x in ids} and mate not in extras:
                extras.append(mate)
        ids.extend(extras)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in ids:
        entry = resolve_lora_entry(raw)
        lid = entry["id"]
        if lid in seen:
            continue
        seen.add(lid)
        w = (weights or {}).get(lid, entry.get("default_weight", 0.6))
        out.append(
            {
                "id": lid,
                "file": entry["filename"],
                "weight": float(w),
                "branch": entry.get("branch", "both"),
            }
        )
    return out


def infer_moe_branch_from_filename(name: str) -> str | None:
    """Infer MoE expert from common Wan LoRA filenames (*High* / *Low* / *high_noise*).

    Returns 'high', 'low', or None if ambiguous. Never swap High↔Low.
    """
    stem = name.rsplit("\\", 1)[-1].rsplit("/", 1)[-1].lower()
    # Order matters: high_noise / low_noise before bare high/low.
    if "high_noise" in stem or "_high" in stem or stem.endswith("high.safetensors"):
        return "high"
    if "low_noise" in stem or "_low" in stem or stem.endswith("low.safetensors"):
        return "low"
    if "-high-" in stem or ".high." in stem:
        return "high"
    if "-low-" in stem or ".low." in stem:
        return "low"
    return None


def resolve_moe_lora_stacks(
    lora_ids: list[str] | None = None,
    *,
    bundle: str = "",
    weights: dict[str, float] | None = None,
    loras: list[dict[str, Any]] | None = None,
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """Split resolved LoRAs into HIGH / LOW stacks for Wan 2.2 MoE.

    Lightning distill LoRAs are applied by `build_wan22_i2v_moe_api` when
    use_lightning=True — exclude them from these stacks to avoid double-loading.
    Explicit branch wins; else catalog branch; else filename (*High*→high, *Low*→low).
    """
    skip = {"lightning_i2v_high", "lightning_i2v_low"}
    resolved = loras if loras is not None else resolve_lora_list(lora_ids, bundle=bundle, weights=weights)
    high: list[tuple[str, float]] = []
    low: list[tuple[str, float]] = []
    for item in resolved:
        lid = str(item.get("id") or "")
        if lid in skip:
            continue
        name = str(item.get("file") or item.get("name") or "")
        if not name:
            continue
        weight = float(item.get("weight", 0.6))
        branch = str(item.get("branch") or "").lower().strip()
        if not branch:
            branch = str(WAN_VIDEO_LORAS.get(lid, {}).get("branch") or "").lower().strip()
        if not branch:
            # Filename safety net only when branch unset (never override explicit "both").
            branch = infer_moe_branch_from_filename(name) or "both"
        if branch in {"high", "both"}:
            high.append((name, weight))
        if branch in {"low", "both"}:
            low.append((name, weight))
    return high, low


def check_wan_video_loras(cfg: dict[str, Any], lora_ids: list[str] | None = None) -> dict[str, Any]:
    dirs = model_dirs(cfg)
    lora_dir = dirs.get("loras")
    entries = (
        [resolve_lora_entry(i) for i in lora_ids]
        if lora_ids
        else list(WAN_VIDEO_LORAS.values())
    )
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for entry in entries:
        found = _find_file(entry["filename"], dirs, "loras")
        item = {k: entry[k] for k in ("id", "filename", "purpose", "default_weight", "size_hint") if k in entry}
        if found:
            installed.append({**item, "path": str(found)})
        else:
            missing.append(item)
    return {
        "installed": installed,
        "missing": missing,
        "ready": len(missing) == 0,
        "bundles": WAN_VIDEO_LORA_BUNDLES,
        "catalog": {k: v.get("purpose", "") for k, v in WAN_VIDEO_LORAS.items()},
    }


def download_wan_video_loras(
    cfg: dict[str, Any],
    *,
    lora_ids: list[str] | None = None,
    bundle: str = "",
    force: bool = False,
) -> list[dict[str, Any]]:
    resolved = resolve_lora_list(lora_ids, bundle=bundle)
    if bundle and not resolved:
        raise ValueError(f"Unknown bundle: {bundle!r}. Known: {list(WAN_VIDEO_LORA_BUNDLES)}")
    if not resolved and lora_ids:
        resolved = resolve_lora_list(lora_ids)

    targets = resolved or [
        {"id": e["id"], "file": e["filename"], "weight": e.get("default_weight", 0.6)}
        for e in WAN_VIDEO_LORAS.values()
    ]
    results: list[dict[str, Any]] = []
    for item in targets:
        entry = resolve_lora_entry(item["id"])
        if not entry.get("repo") or not entry.get("path"):
            found = _find_file(entry["filename"], model_dirs(cfg), "loras")
            results.append(
                {
                    "id": entry["id"],
                    "filename": entry["filename"],
                    "ok": bool(found),
                    "path": str(found) if found else None,
                    "skipped": True,
                    "reason": "local-only (no HF repo)",
                }
            )
            continue
        try:
            path = download_asset(cfg, entry, force=force)
            results.append({"id": entry["id"], "filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"id": entry["id"], "filename": entry["filename"], "ok": False, "error": str(exc)})
    return results
