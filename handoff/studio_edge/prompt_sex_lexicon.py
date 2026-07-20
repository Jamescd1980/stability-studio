"""House lexicon for NSFW Illustrious / waijfu_alpha prompts (Myra/Nari path).

waijfu_alpha prefers: short vulgar scene DESCRIPTION + explicit sex-act tags.
Never say \"camera\" (spawns props); say view / POV instead.
"""
from __future__ import annotations

SEX_PROMPT_DIRECTIVE = (
    "For waijfu_alpha sexual content use the Invoke-style layered prompt: "
    "quality/scene, style (anime++), then 'View from mans POV' (never camera), "
    "then a vulgar action sentence, then sex-act tags. "
    "Example: 'View from mans POV, 1girl, Frieren, silver hair, naked, "
    "looking back over her shoulder, on her hands and knees, "
    "man behind her shoving his cock in her pussy, man grabs her hips, "
    "doggystyle, vaginal penetration'. "
    "Hole swap: 'shoving his cock in her ass' + 'anal sex' vs "
    "'shoving his cock in her pussy' + 'vaginal penetration'. "
    "Toys: say 'dildo' and describe type/color/size "
    "(thick purple dildo, realistic flesh-colored dildo) — never vague 'sex toy'. "
    "'vibrator' ONLY means the small wired bullet/wand vibe, not a dildo. "
    "Do NOT soften with gentle/intimate euphemisms. "
    "Canonical examples: D:\\Invoke AI\\outputs\\images (invokeai_metadata)."
)

CAMERA_PROP_NEGATIVE = (
    "camera, dslr, camcorder, lens, smartphone, selfie stick, "
    "tripod, photographer, holding camera"
)

# Soft → blunt replacements applied to expanded prompts / VLM tags
SOFT_TO_EXPLICIT = (
    (r"\bgently rubbing (?:her )?clit\b", "fingering her pussy"),
    (r"\brubbing (?:her )?clit\b", "fingering her pussy"),
    (r"\btouching herself\b", "fingering her pussy"),
    (r"\bself[\s-]?touch\b", "masturbation, fingering her pussy"),
    (r"\bintimate self[\s-]?touch\b", "fingering her pussy"),
    (r"\brear entry\b", "doggystyle, anal sex"),
    (r"\bmaking love\b", "vaginal sex"),
    # Vague toy → dildo; vibrator left alone (wired vibe only — not a dildo synonym)
    (r"\bsex[\s-]?toys?\b", "dildo"),
    (r"\badult toys?\b", "dildo"),
    (r"\bcamera angle\b", "view"),
    (r"\blow camera\b", "from below"),
    (r"\bcamera POV\b", "man's POV"),
    (r"\bcinematic camera\b", "cinematic view"),
    (r"\bshot on camera\b", "looking at viewer"),
)
