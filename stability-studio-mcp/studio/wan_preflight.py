"""Wan I2V preflight helpers — gate clips, plan beats, prompt hygiene, polish advice.

Prevents common LESSONS-WAN-I2V mistakes before/after generate_video.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from studio.video_utils import extract_last_frame, probe_video
from studio.wan_video_loras import suggest_wan_action_lora

ROOT = Path(__file__).resolve().parents[1]
EBSYNTH_EXE = ROOT / "tools" / "ebsynth" / "ebsynth.exe"

# Prompt hygiene patterns (NSFW Wan keepers)
_CAMERA_RE = re.compile(r"\b(camera|dslr|camcorder|lens|smartphone)\b", re.I)
_FEMALE_CUM_RE = re.compile(r"\bfemale\s+cum\b|\bshe\s+cums\b|\bher\s+cum\b", re.I)
_FULL_EXIT_RE = re.compile(
    r"\b(full\s+(penis\s+)?exit|slides?\s+out|pulls?\s+out\s+completely|"
    r"empty\s+(mouth|vagina|pussy)|tip\s+outside)\b",
    re.I,
)
_HEAD_STILL_RE = re.compile(
    r"\b(head\s+completely\s+still|head\s+frozen|no\s+head\s+motion|"
    r"face\s+nearly\s+still)\b",
    re.I,
)
_EYE_MOUTH_RE = re.compile(
    r"\b(detailed\s+(face|eyes)|symmetrical\s+eyes|perfect\s+eyes|"
    r"looking\s+at\s+viewer|eye\s+contact|open\s+mouth|tongue\s+out)\b",
    re.I,
)
_VERBISH = re.compile(
    r"\b(bobs?|slides?|pushes?|thrusts?|pumps?|bounces?|lifts?|"
    r"withdraws?|bur(?:y|ies)|swallows?|nods?|shakes?)\b",
    re.I,
)


def check_ebsynth() -> dict[str, Any]:
    """Verify real jamriska ebsynth.exe (not OpenCV fallback / PyPI stub)."""
    present = EBSYNTH_EXE.is_file() and EBSYNTH_EXE.stat().st_size > 50_000
    return {
        "ok": present,
        "ebsynth_exe": str(EBSYNTH_EXE),
        "present": present,
        "bytes": EBSYNTH_EXE.stat().st_size if EBSYNTH_EXE.is_file() else 0,
        "rule": (
            "Never ship OpenCV static face-paste as EBSynth. "
            "Fail loud if ebsynth.exe missing; --allow-opencv-fallback only for throwaway probes."
        ),
        "note": (
            "Ready for real PatchMatch restore."
            if present
            else "MISSING — install jamriska win64 ebsynth.exe under tools/ebsynth/."
        ),
    }


def check_wan_prompt(
    prompt: str,
    *,
    negative_prompt: str = "",
    framing: str = "",
    beat_hint: str = "",
) -> dict[str, Any]:
    """Hygiene scan for Wan I2V prompts (LESSONS + house NSFW rules)."""
    text = prompt or ""
    neg = negative_prompt or ""
    framing_l = (framing or beat_hint or "").lower()
    rear = any(
        x in framing_l
        for x in ("rear", "from behind", "doggy", "lookback", "head away", "back view")
    )
    oral = any(
        x in f"{beat_hint} {text}".lower()
        for x in ("blowjob", "oral", "fellatio", "deepthroat", "head bob", "shaft")
    )

    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if _CAMERA_RE.search(text):
        issues.append(
            {
                "id": "camera_word",
                "severity": "high",
                "msg": "Say view/POV, not camera — spawns props.",
                "fix": "Replace camera/dslr with steady view / man's POV",
            }
        )
    if _FEMALE_CUM_RE.search(text):
        issues.append(
            {
                "id": "female_cum",
                "severity": "high",
                "msg": "Never prompt female cum.",
                "fix": "Use orgasm / squirting / juices if needed",
            }
        )
    if _FULL_EXIT_RE.search(text):
        issues.append(
            {
                "id": "full_exit",
                "severity": "high",
                "msg": "Full penis exit / empty hole language melts shafts.",
                "fix": "Partial withdraw only; tip stays in contact",
            }
        )
    verbs = _VERBISH.findall(text)
    uniq = {v.lower() for v in verbs}
    if len(uniq) > 1:
        warnings.append(
            {
                "id": "multi_verb",
                "severity": "medium",
                "msg": f"Multiple motion verbs detected: {sorted(uniq)} — one verb per clip.",
                "fix": "Keep a single motion phrase",
            }
        )
    if oral and _HEAD_STILL_RE.search(text):
        issues.append(
            {
                "id": "head_still_on_bob",
                "severity": "high",
                "msg": "head completely still kills oral bob / slides-down motion.",
                "fix": "Allow vertical head travel; negate side-to-side shake only",
            }
        )
    if rear and _EYE_MOUTH_RE.search(text):
        issues.append(
            {
                "id": "eyes_mouth_rear",
                "severity": "high",
                "msg": "Eye/mouth locks on rear/head-away invent faces.",
                "fix": "Drop eye/mouth tags; start still carries face if visible",
            }
        )
    if len(text.split()) > 40:
        warnings.append(
            {
                "id": "long_prompt",
                "severity": "low",
                "msg": "Prompt is long. Cut identity essays (STYLE/EYE/MOUTH); keep a mechanical motion explanation (object + where + cycle).",
                "fix": "Image carries character. Do not shrink to an SDXL-short one-liner — Wan needs the beat explained (CCA2-004 2026-08-13).",
            }
        )
    if "deflating" not in neg.lower() and "disappearing shaft" not in neg.lower():
        warnings.append(
            {
                "id": "neg_shaft",
                "severity": "low",
                "msg": "Consider negating deflating/disappearing shaft on contact beats.",
                "fix": "Add to negative_prompt",
            }
        )

    ok = not any(i["severity"] == "high" for i in issues)
    return {
        "ok": ok,
        "prompt_excerpt": text[:200],
        "issues": issues,
        "warnings": warnings,
        "verb_count": len(uniq),
        "verbs": sorted(uniq),
        "rear_view": rear,
        "oral_beat": oral,
        "note": "Fix high issues before generate_video keepers.",
    }


def plan_wan_beat(
    *,
    beat_hint: str = "",
    still_notes: str = "",
    prompt: str = "",
    hard_contact: bool = False,
    dual_face: bool = False,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map tip-vs-already-in / pose family → LoRA bundle + frames + verb template."""
    blob = f"{beat_hint}\n{still_notes}\n{prompt}".lower()
    tip_still = any(
        x in blob
        for x in (
            "tip at",
            "tip-at",
            "tip only",
            "just outside",
            "entrance",
            "not buried",
            "shallow",
        )
    )
    already_in = any(
        x in blob
        for x in (
            "already in",
            "already-in",
            "buried",
            "deep inside",
            "cock in pussy",
            "cock in her",
            "tip in mouth",
            "in mouth",
        )
    )
    doggy = any(x in blob for x in ("doggy", "from behind", "rear", "all fours"))
    oral = any(
        x in blob for x in ("blowjob", "oral", "fellatio", "deepthroat", "mouth", "bj")
    )
    facial = any(x in blob for x in ("facial", "cum on face", "cumshot on face"))
    insert = tip_still or any(
        x in blob for x in ("push in", "insertion", "tip→in", "bury", "slides in")
    )

    if facial:
        kind = "facial"
        bundle = "facial_cum"
        verb = "thick white cum shoots onto her face"
        frames = 49
    elif oral:
        kind = "oral"
        bundle = "oral_insertion"
        verb = "her head slides down the shaft taking the cock deeper"
        frames = 33 if hard_contact else 49
        if "still" in blob and "head" in blob:
            verb = "her head slides down the shaft taking the cock deeper"
    elif doggy:
        kind = "doggy_thrust" if already_in or not tip_still else "doggy_insert"
        bundle = "doggy_sex"
        verb = (
            "short front-to-back hip thrusts, cock stays inside"
            if kind == "doggy_thrust"
            else "he pushes in from behind and stays buried"
        )
        frames = 21 if hard_contact or dual_face else 49
    elif insert and tip_still and not already_in:
        kind = "insert_tip_to_in"
        bundle = "pov_insertion"
        verb = "he slowly pushes his cock into her pussy and stays buried"
        frames = 49
    else:
        kind = "thrust_already_in"
        bundle = "missionary_sex"
        verb = "short front-to-back thrusts, partial withdraw only, cock stays inside"
        frames = 21 if hard_contact or dual_face else 49

    lora = suggest_wan_action_lora(verb, beat_hint=bundle, cfg=cfg)
    warnings: list[str] = []
    if tip_still and bundle == "missionary_sex":
        warnings.append(
            "Tip-at-entrance still + Missionary Sex usually fails — use pov_insertion "
            "or paint already-in still first."
        )
    if doggy and "missionary" in blob:
        warnings.append("Doggy still + Missionary Sex = wrong pose family.")
    if dual_face and frames > 21:
        warnings.append("Dual-face hard contact: prefer 21f micro-thrust then splice.")

    return {
        "ok": True,
        "beat_kind": kind,
        "recommended_bundle": bundle,
        "lora_ready": bool(lora.get("ready")),
        "lora_missing": lora.get("missing") or [],
        "num_frames": frames,
        "frame_rate": 16,
        "moe_preset": "quality",
        "workflow_id": "i2v",
        "suggested_prompt": verb,
        "negative_hints": (
            "full penis exit, empty vagina, empty mouth, tip outside, "
            "deflating shaft, disappearing shaft, melting, morphing face, camera, dslr"
        ),
        "still_prep": (
            "Tip still resists bury — Forge/paint already-in contact before thrust LoRA"
            if tip_still and kind.startswith("thrust")
            else "Start still OK for this LoRA class"
            if already_in or oral
            else "Confirm tip-in-mouth / tip-at-entrance matches chosen LoRA"
        ),
        "warnings": warnings,
        "generate_video_args": {
            "workflow_id": "i2v",
            "moe_preset": "quality",
            "lora_bundle": bundle,
            "num_frames": frames,
            "frame_rate": 16,
            "prompt": verb,
        },
        "checklist": [
            "Confirm still type (tip vs already-in) matches beat_kind",
            "resolve_wan_action_loras / download if missing",
            "check_wan_prompt on final prompt",
            "generate_video quality MoE one verb",
            "gate_i2v_clip before keep/chain",
        ],
    }


def _load_rgb(path: Path):
    from PIL import Image
    import numpy as np

    im = Image.open(path).convert("RGB")
    return im, np.asarray(im, dtype="float32")


def _extract_at(video: Path, dest: Path, time_sec: float) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(time_sec),
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    if not dest.is_file() or dest.stat().st_size < 500:
        raise RuntimeError(f"frame extract failed: {dest}")
    return dest


def gate_i2v_clip(
    video_path: str | Path,
    *,
    start_image_path: str | Path = "",
    work_dir: str | Path = "",
) -> dict[str, Any]:
    """Gate f0 / mid / last vs optional start still (identity + motion sanity)."""
    import numpy as np

    video = Path(video_path)
    if not video.is_file():
        return {"ok": False, "error": f"video not found: {video}"}
    info = probe_video(video)
    dur = float(info.get("duration_sec") or 0) or max(
        0.1, float(info.get("frame_count") or 1) / float(info.get("fps") or 16)
    )
    work = Path(work_dir) if work_dir else video.parent / f"_gate_{video.stem}"
    work.mkdir(parents=True, exist_ok=True)

    times = {"f0": 0.0, "mid": max(0.0, dur * 0.5), "last": max(0.0, dur - 0.05)}
    frames: dict[str, Path] = {}
    for tag, t in times.items():
        frames[tag] = _extract_at(video, work / f"{tag}.png", t)

    arrs = {k: _load_rgb(p)[1] for k, p in frames.items()}
    # resize all to f0 size
    from PIL import Image

    h0, w0 = arrs["f0"].shape[:2]

    def resize(a):
        if a.shape[0] == h0 and a.shape[1] == w0:
            return a
        im = Image.fromarray(a.astype("uint8")).resize((w0, h0), Image.Resampling.LANCZOS)
        return np.asarray(im, dtype="float32")

    for k in list(arrs):
        arrs[k] = resize(arrs[k])

    def mse(a, b) -> float:
        return float(np.mean((a - b) ** 2))

    face = (
        slice(int(0.05 * h0), int(0.45 * h0)),
        slice(int(0.2 * w0), int(0.8 * w0)),
    )

    metrics = {
        "f0_vs_mid_mse": mse(arrs["f0"], arrs["mid"]),
        "f0_vs_last_mse": mse(arrs["f0"], arrs["last"]),
        "mid_vs_last_mse": mse(arrs["mid"], arrs["last"]),
        "face_f0_vs_mid_mse": mse(arrs["f0"][face], arrs["mid"][face]),
        "face_f0_vs_last_mse": mse(arrs["f0"][face], arrs["last"][face]),
    }

    start_mse = None
    start_path = Path(start_image_path) if start_image_path else None
    if start_path and start_path.is_file():
        s = resize(_load_rgb(start_path)[1])
        start_mse = mse(arrs["f0"], s)
        metrics["f0_vs_start_still_mse"] = start_mse

    # Heuristic pass/fail (tune from Saloon BJ: good f0-still ~13; melt faces >> 200)
    flags: list[str] = []
    ok = True
    if start_mse is not None and start_mse > 120:
        ok = False
        flags.append("f0_identity_drift_vs_start_still")
    if metrics["face_f0_vs_mid_mse"] > 400:
        ok = False
        flags.append("mid_face_melt_suspect")
    if metrics["f0_vs_last_mse"] < 15:
        flags.append("little_global_motion_f0_to_last")
    if metrics["face_f0_vs_last_mse"] < 8 and metrics["f0_vs_last_mse"] < 30:
        flags.append("almost_static_clip")

    return {
        "ok": ok,
        "video": str(video),
        "probe": info,
        "frames": {k: str(v) for k, v in frames.items()},
        "metrics": metrics,
        "flags": flags,
        "verdict": "pass_candidate" if ok else "fail_review",
        "note": (
            "Human must still approve keepers. "
            "fail_review = do not chain; diagnose break frames before retry."
        ),
        "work_dir": str(work),
    }


def extract_chain_lastframe(
    video_path: str | Path,
    *,
    output_path: str | Path = "",
    start_image_path: str | Path = "",
) -> dict[str, Any]:
    """Extract last frame for chain + usability score vs start / f0."""
    import numpy as np
    from PIL import Image

    video = Path(video_path)
    if not video.is_file():
        return {"ok": False, "error": f"video not found: {video}"}
    dest = Path(output_path) if output_path else video.with_name(f"{video.stem}_lastframe.png")
    extract_last_frame(video, dest)

    gate = gate_i2v_clip(video, start_image_path=start_image_path)
    last = np.asarray(Image.open(dest).convert("RGB"), dtype="float32")
    f0_path = Path(gate["frames"]["f0"]) if gate.get("frames") else None
    usable = True
    reasons: list[str] = []
    if f0_path and f0_path.is_file():
        f0 = np.asarray(
            Image.open(f0_path).convert("RGB").resize(
                (last.shape[1], last.shape[0]), Image.Resampling.LANCZOS
            ),
            dtype="float32",
        )
        m = float(np.mean((last - f0) ** 2))
        if m < 10:
            reasons.append("last≈f0 (little motion) — weak chain progress")
        if m > 2500:
            usable = False
            reasons.append("last far from f0 — possible melt/teleport")
    if not gate.get("ok"):
        usable = False
        reasons.extend(gate.get("flags") or ["gate_failed"])

    return {
        "ok": True,
        "lastframe": str(dest),
        "usable_for_chain": usable,
        "reasons": reasons,
        "gate": gate,
        "note": (
            "Human must approve before next I2V link. Never chain a fail."
            if usable
            else "Do not chain — recycle/retry this link."
        ),
    }


def recommend_polish(
    video_path: str | Path = "",
    *,
    eyes_melted: bool = False,
    already_looks_good: bool = False,
    user_prefers_no_rife: bool = True,
) -> dict[str, Any]:
    """Advise polish path (SeedVR @16fps / none / avoid RIFE)."""
    video = Path(video_path) if video_path else None
    probe = probe_video(video) if video and video.is_file() else None
    if eyes_melted:
        return {
            "ok": True,
            "recommend": "none_or_trim_only",
            "skip_rife": True,
            "skip_seedvr": True,
            "reason": "RIFE→SeedVR invents more mush on melted eyes — fix gen/trim first.",
            "tool": None,
            "probe": probe,
        }
    if already_looks_good:
        return {
            "ok": True,
            "recommend": "none",
            "skip_rife": True,
            "skip_seedvr": True,
            "reason": "Master already good — polish can soften (BJ02 SeedVR lesson).",
            "tool": None,
            "probe": probe,
        }
    if user_prefers_no_rife:
        return {
            "ok": True,
            "recommend": "seedvr_only_1080",
            "skip_rife": True,
            "skip_seedvr": False,
            "reason": "SeedVR @ native 16fps only — no RIFE (Saloon house preference).",
            "tool": "polish_wan_best",
            "args": {
                "skip_interpolate": True,
                "seedvr2_resolution": 1080,
                "seedvr2_batch_size": 5,
                "seedvr2_blocks_to_swap": 16,
            },
            "probe": probe,
            "gate_after": "Compare vs dim master; recycle if softer/worse.",
        }
    return {
        "ok": True,
        "recommend": "rife_then_seedvr",
        "skip_rife": False,
        "skip_seedvr": False,
        "reason": "Legacy best_free path — only if user accepts RIFE.",
        "tool": "polish_wan_best",
        "args": {"skip_interpolate": False, "target_fps": 24, "seedvr2_resolution": 1080},
        "probe": probe,
    }
