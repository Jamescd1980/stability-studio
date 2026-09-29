"""Tight face Forge refine + Nari pass/fail review loop.

Mirrors the human stills workflow:
  detect/box face → low denoise region inpaint → review → retry or fail.

Denoise policy (face Forge):
  eyes_only / oral lock: 0.05–0.10
  face_soft:             0.08–0.12
  face_refine (default): 0.12–0.18
  face_rescue:           0.18–0.22
  Auto presets stay ≤0.25. Explicit denoise= override may go up to 0.45
  (strong rewrite / marking removal — agent or user must pass denoise intentionally).
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

import requests

from studio.forge_backend import (
    forge_is_reachable,
    forge_url,
    inspect_forge_backend,
)
from studio.nari_ollama import ollama_base_url, _nari_cfg

# --- denoise presets ---------------------------------------------------------

FACE_DENOISE_PRESETS: dict[str, dict[str, Any]] = {
    "eyes_only": {
        "denoise": 0.08,
        "ad_model": "mediapipe_face_mesh_eyes_only",
        "padding": 48,
        "pad_frac": 0.04,
        "note": "Eyes / oral lock — keep mouth and body frozen",
    },
    "face_soft": {
        "denoise": 0.10,
        "ad_model": "face_yolov8n.pt",
        "padding": 56,
        "pad_frac": 0.06,
        "note": "Light expression / skin clean",
    },
    "face_refine": {
        "denoise": 0.15,
        "ad_model": "face_yolov8n.pt",
        "padding": 64,
        "pad_frac": 0.08,
        "note": "Default identity-safe face pass",
    },
    "face_rescue": {
        "denoise": 0.20,
        "ad_model": "face_yolov8n.pt",
        "padding": 72,
        "pad_frac": 0.10,
        "note": "Harder fix — still under 0.25; review carefully",
    },
}

MAX_AUTO_DENOISE = 0.25
MAX_EXPLICIT_DENOISE = 0.45

NARI_FACE_CRITERIA = """You are Nari reviewing a Forge FACE refine (before/after stills).
The AFTER must only change the FACE region. Body, clothes, hands, and background must match BEFORE.

PASS only if ALL are true:
1) Same person / identity as BEFORE — especially SAME eye color, SAME hair color, and SAME tattoos / face markings (cheek marks, forehead glyphs, freckles, scars, facial tattoos, paint). Also age and face shape.
2) Face sits naturally on the neck/shoulders — no floating head or seam halo.
3) Lower half of the frame (chest, hands, torso, background below chin) matches BEFORE — no global redraw; body tattoos on neck/shoulders unchanged.
4) Expression matches the requested face prompt if one was given (open/closed mouth, smirk, etc.).
5) No obvious double-face, melted features, or plastic sheen that was not in BEFORE.

FAIL if ANY are true:
- Eye color changed (e.g. brown→blue, green→gold) vs BEFORE.
- Hair color changed (e.g. silver→blonde, black→brown) vs BEFORE unless the prompt explicitly requested a recolor.
- Tattoos or face markings removed, moved, reshaped, recolored, or newly invented vs BEFORE (unless the prompt explicitly requested that edit).
- Top half looks freshly regenerated while the bottom does not match (classic bad ADetailer / full-frame bake).
- Identity drift (different person).
- Hard rectangular or oval patch / color mismatch around the face.
- Mouth/body contact geometry changed when the job was face-only.
- Over-smoothed plastic face vs a sharper body.

Reply with EXACTLY this JSON (no markdown):
{"pass": true|false, "score": 0-100, "reasons": ["short bullet", "..."], "summary": "one sentence", "eye_color_match": true|false, "hair_color_match": true|false, "markings_match": true|false}
"""


def face_denoise_guide() -> dict[str, Any]:
    return {
        "ok": True,
        "max_auto_denoise": MAX_AUTO_DENOISE,
        "max_explicit_denoise": MAX_EXPLICIT_DENOISE,
        "presets": FACE_DENOISE_PRESETS,
        "policy": (
            "Tight face box + inpaint_full_res. Preset denoise 0.05–0.20 for keepers; "
            "auto cap 0.25. Pass denoise= explicitly for strong rewrites up to 0.45 "
            "(e.g. marking removal / complete face rewrite). One face per pass. "
            "Before Forge: note eye + hair color and any tattoos/face markings from the source "
            "and lock them in the prompt; fail/revert if eyes, hair, or markings drift "
            "(unless the prompt explicitly requested that change)."
        ),
        "workflow": [
            "Look at source still — note eye color, hair color, tattoos/face markings (or none)",
            "switch_stills_backend(forge)",
            "refine_face_forge(image_path, face_prompt=... include colors + markings + expression, denoise=0.35 if strong rewrite)",
            "If nari_review.pass=false (incl. eye/hair/marking drift) → revert; do not send to user",
            "Human views saved_files[0] only after nari_review.pass=true",
            "switch_stills_backend(comfy) before video",
        ],
        "identity_lock": {
            "eye_color": "Required in face_prompt unless user explicitly changes eyes",
            "hair_color": "Required in face_prompt unless user explicitly recolors hair",
            "tattoos_face_markings": (
                "Describe existing marks (placement/shape/color) or explicitly say none; "
                "fail if removed, moved, or invented — unless prompt requested the change"
            ),
            "on_mismatch": "fail + revert to original",
        },
    }


def _b64_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _b64_pil(im: Any, fmt: str = "PNG") -> str:
    import io

    buf = io.BytesIO()
    im.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _ensure_forge(cfg: dict[str, Any]) -> dict[str, Any] | None:
    from studio.gpu_backend import comfyui_is_reachable

    url = forge_url(cfg)
    if not url:
        return {"ok": False, "error": "forge.url not configured"}
    if not forge_is_reachable(cfg):
        return {
            "ok": False,
            "error": "Forge is not reachable. Call switch_stills_backend(backend='forge') first.",
            "forge": inspect_forge_backend(cfg),
        }
    if comfyui_is_reachable(cfg):
        return {
            "ok": False,
            "error": (
                "ComfyUI is still running — exclusive GPU. "
                "Call switch_stills_backend(backend='forge') first."
            ),
        }
    return None


def _resolve_preset(preset: str, denoise: float | None) -> dict[str, Any]:
    key = (preset or "face_refine").strip().lower().replace("-", "_")
    if key not in FACE_DENOISE_PRESETS:
        key = "face_refine"
    spec = dict(FACE_DENOISE_PRESETS[key])
    spec["preset"] = key
    if denoise is not None:
        d = float(denoise)
        # Explicit denoise= is intentional — allow up to MAX_EXPLICIT_DENOISE
        cap = MAX_EXPLICIT_DENOISE
        if d > cap:
            spec["denoise_capped"] = True
            spec["denoise_requested"] = d
            d = cap
        spec["denoise"] = max(0.03, min(cap, d))
        if float(denoise) > MAX_AUTO_DENOISE:
            spec["explicit_high_denoise"] = True
    return spec


def _yolo_weight_candidates() -> list[Path]:
    cands = [
        Path.home() / ".cache" / "ultralytics" / "face_yolov8n.pt",
        Path(r"D:\Extra Models") / "adetailer" / "face_yolov8n.pt",
        Path(r"D:\Extra Models") / "adetailer" / "face_yolov8m.pt",
        Path(r"D:\sd-webui-forge\models\adetailer\face_yolov8n.pt"),
        Path(r"D:\StabilityMatrix-win-x64\Data\Packages\ComfyUI\models\ultralytics\bbox\face_yolov8n.pt"),
        Path(r"D:\StabilityMatrix-win-x64\Data\Packages\ComfyUI\models\ultralytics\bbox\face_yolov8m.pt"),
    ]
    snap = Path(r"D:\sd-webui-forge\models\diffusers")
    if snap.is_dir():
        cands.extend(sorted(snap.rglob("face_yolov8*.pt"))[:4])
    return cands


def _resolve_yolo_weights() -> Path:
    for p in _yolo_weight_candidates():
        if p.is_file():
            return p
    return Path("face_yolov8n.pt")


def _detect_face_yolo_inprocess(
    rgb,
    *,
    w: int,
    h: int,
    face_index: int,
    pad_frac: float,
) -> dict[str, Any] | None:
    from ultralytics import YOLO
    import numpy as np

    model_path = _resolve_yolo_weights()
    yolo = YOLO(str(model_path))
    det = yolo.predict(np.array(rgb), conf=0.15, verbose=False)[0]
    if det.boxes is None or len(det.boxes) == 0:
        return None
    boxes = det.boxes.xyxy.cpu().numpy()
    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
    order = sorted(range(len(boxes)), key=lambda i: areas[i], reverse=True)
    idx = order[min(max(0, face_index), len(order) - 1)]
    x1, y1, x2, y2 = map(int, boxes[idx])
    bw, bh = x2 - x1, y2 - y1
    pad_x, pad_y = int(bw * pad_frac), int(bh * pad_frac * 1.1)
    box = (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(w, x2 + pad_x),
        min(h, y2 + pad_y),
    )
    return {
        "ok": True,
        "box": list(box),
        "method": "yolo",
        "size": [w, h],
        "faces_found": len(boxes),
        "face_index": idx,
    }


def _detect_face_yolo_subprocess(
    image_path: Path,
    *,
    face_index: int,
    pad_frac: float,
) -> dict[str, Any] | None:
    """Run YOLO in an external Python that has ultralytics (One Desk Fresh workaround)."""
    import json
    import subprocess
    import sys

    weights = _resolve_yolo_weights()
    pythons = [
        Path(r"C:\Users\Creel\AppData\Local\Programs\Python\Python314\python.exe"),
        Path(r"D:\studio-agent\desk-ui\.venv\Scripts\python.exe"),
        Path(sys.executable),
    ]
    snippet = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "from ultralytics import YOLO\n"
        "import numpy as np\n"
        "from PIL import Image\n"
        "f,wts,fi,pf=sys.argv[1],sys.argv[2],int(sys.argv[3]),float(sys.argv[4])\n"
        "im=Image.open(f).convert('RGB'); w,h=im.size\n"
        "det=YOLO(wts).predict(np.array(im),conf=0.15,verbose=False)[0]\n"
        "if det.boxes is None or len(det.boxes)==0:\n"
        "  print(json.dumps({'ok':False,'error':'no detections'})); sys.exit(0)\n"
        "boxes=det.boxes.xyxy.cpu().numpy()\n"
        "areas=[(b[2]-b[0])*(b[3]-b[1]) for b in boxes]\n"
        "order=sorted(range(len(boxes)), key=lambda i: areas[i], reverse=True)\n"
        "idx=order[min(max(0,fi), len(order)-1)]\n"
        "x1,y1,x2,y2=map(int, boxes[idx]); bw,bh=x2-x1,y2-y1\n"
        "px,py=int(bw*pf), int(bh*pf*1.1)\n"
        "box=[max(0,x1-px), max(0,y1-py), min(w,x2+px), min(h,y2+py)]\n"
        "print(json.dumps({'ok':True,'box':box,'method':'yolo_ext','size':[w,h],"
        "'faces_found':len(boxes),'face_index':idx}))\n"
    )
    seen: set[str] = set()
    for py in pythons:
        key = str(py).lower()
        if not py.is_file() or key in seen:
            continue
        seen.add(key)
        try:
            proc = subprocess.run(
                [str(py), "-c", snippet, str(image_path), str(weights), str(face_index), str(pad_frac)],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            continue
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            continue
        if data.get("ok") and data.get("box"):
            return data
    return None


def detect_face_box(
    image_path: str | Path,
    *,
    face_index: int = 0,
    pad_frac: float = 0.08,
) -> dict[str, Any]:
    """Return {ok, box:[x1,y1,x2,y2], method, size} for a tight face frame."""
    from PIL import Image

    src = Path(image_path)
    if not src.is_file():
        return {"ok": False, "error": f"image not found: {image_path}"}
    with Image.open(src) as im:
        w, h = im.size
        rgb = im.convert("RGB")

    yolo_err = "unavailable"
    # 1) in-process ultralytics
    try:
        hit = _detect_face_yolo_inprocess(rgb, w=w, h=h, face_index=face_index, pad_frac=pad_frac)
        if hit:
            return hit
        yolo_err = "no detections"
    except Exception as exc:
        yolo_err = str(exc)
        # 1b) external Python (Desk Fresh often lacks ultralytics in the frozen runtime)
        try:
            ext = _detect_face_yolo_subprocess(src, face_index=face_index, pad_frac=pad_frac)
            if ext:
                return ext
        except Exception as ext_exc:
            yolo_err = f"{yolo_err}; ext={ext_exc}"

    # 2) heuristic upper-center face frame (~portrait)
    fw, fh = int(w * 0.42), int(h * 0.38)
    cx, cy = w // 2, int(h * 0.32)
    box = (
        max(0, cx - fw // 2),
        max(0, cy - fh // 2),
        min(w, cx + fw // 2),
        min(h, cy + fh // 2),
    )
    return {
        "ok": True,
        "box": list(box),
        "method": "heuristic_upper_center",
        "size": [w, h],
        "warning": f"YOLO unavailable or empty ({yolo_err}); using heuristic box — verify frame preview",
    }


def _ellipse_mask(size: tuple[int, int], box: tuple[int, int, int, int], blur: int = 5):
    from PIL import Image, ImageDraw, ImageFilter

    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(list(box), fill=255)
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur))
    return mask


def _save_frame_preview(src: Path, box: tuple[int, int, int, int], dest: Path) -> Path:
    from PIL import Image, ImageDraw

    with Image.open(src) as im:
        prev = im.convert("RGB").copy()
    ImageDraw.Draw(prev).rectangle(list(box), outline=(255, 60, 60), width=3)
    dest.parent.mkdir(parents=True, exist_ok=True)
    prev.save(dest)
    return dest


def region_face_inpaint(
    cfg: dict[str, Any],
    *,
    image_path: str | Path,
    box: tuple[int, int, int, int],
    prompt: str,
    negative_prompt: str = "",
    denoise: float = 0.15,
    steps: int = 28,
    cfg_scale: float = 5.5,
    seed: int = -1,
    padding: int = 64,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    """Forge img2img with ellipse face mask + inpaint_full_res (tight zoom)."""
    err = _ensure_forge(cfg)
    if err:
        return err

    src = Path(image_path)
    if not src.is_file():
        return {"ok": False, "error": f"image not found: {image_path}"}

    from PIL import Image

    url = forge_url(cfg)
    g = cfg.get("forge") or {}
    timeout = float(g.get("generate_timeout_seconds") or 900)

    with Image.open(src) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size

    x1, y1, x2, y2 = [int(v) for v in box]
    box_t = (max(0, x1), max(0, y1), min(w, x2), min(h, y2))
    if box_t[2] <= box_t[0] or box_t[3] <= box_t[1]:
        return {"ok": False, "error": f"invalid face box: {box}"}

    root = Path(cfg.get("_package_root") or ".") / "outputs" / "forge_face"
    root.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    out = Path(out_path) if out_path else root / f"face_{stamp}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    mask_path = out.with_name(out.stem + "_mask.png")
    frame_path = out.with_name(out.stem + "_frame.png")

    mask = _ellipse_mask((w, h), box_t, blur=5)
    mask.save(mask_path)
    _save_frame_preview(src, box_t, frame_path)

    d = float(denoise)
    if d > MAX_AUTO_DENOISE:
        d = MAX_AUTO_DENOISE

    payload: dict[str, Any] = {
        "init_images": [_b64_file(src)],
        "mask": _b64_pil(mask),
        "prompt": prompt,
        "negative_prompt": negative_prompt
        or "blurry face, deformed face, bad anatomy, identity change, plastic skin, seam, halo",
        "denoising_strength": d,
        "steps": int(steps),
        "cfg_scale": float(cfg_scale),
        "width": w,
        "height": h,
        "sampler_name": "Euler a",
        "seed": int(seed),
        "mask_blur": 4,
        "inpainting_fill": 1,
        "inpaint_full_res": True,
        "inpaint_full_res_padding": int(padding),
        "batch_size": 1,
    }
    r = requests.post(f"{url}/sdapi/v1/img2img", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    images = data.get("images") or []
    if not images:
        return {"ok": False, "error": "Forge returned no images", "info": data.get("info")}
    raw = images[0]
    if "," in raw[:64]:
        raw = raw.split(",", 1)[1]
    out.write_bytes(base64.b64decode(raw))

    return {
        "ok": True,
        "backend": "forge",
        "mode": "region_face_inpaint",
        "source": str(src),
        "saved_files": [str(out)],
        "mask_path": str(mask_path),
        "frame_preview": str(frame_path),
        "box": list(box_t),
        "denoising_strength": d,
        "inpaint_full_res_padding": int(padding),
        "info": data.get("info"),
    }


def heuristic_face_gate(
    before_path: str | Path,
    after_path: str | Path,
    *,
    box: list[int] | tuple[int, int, int, int] | None = None,
) -> dict[str, Any]:
    """Pixel gate: lower body must match; face may change within bounds."""
    import numpy as np
    from PIL import Image

    before = Path(before_path)
    after = Path(after_path)
    if not before.is_file() or not after.is_file():
        return {"ok": False, "pass": False, "error": "before/after missing"}

    with Image.open(before) as b_im, Image.open(after) as a_im:
        b = np.asarray(b_im.convert("RGB").resize(a_im.size, Image.Resampling.LANCZOS), dtype="float32")
        a = np.asarray(a_im.convert("RGB"), dtype="float32")

    h, w = b.shape[:2]
    # Lower ~55% of frame should stay nearly identical for face-only refine
    y_cut = int(h * 0.45)
    lower_mse = float(np.mean((b[y_cut:, :] - a[y_cut:, :]) ** 2))
    upper_mse = float(np.mean((b[:y_cut, :] - a[:y_cut, :]) ** 2))

    face_mse = None
    if box and len(box) == 4:
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 > x1 and y2 > y1:
            face_mse = float(np.mean((b[y1:y2, x1:x2] - a[y1:y2, x1:x2]) ** 2))

    flags: list[str] = []
    passed = True
    # Body/background drift = classic "top redone, bottom doesn't match"
    if lower_mse > 35:
        passed = False
        flags.append("lower_half_drift_top_bottom_mismatch")
    if upper_mse < 2 and (face_mse is None or face_mse < 2):
        flags.append("almost_no_change")
    if face_mse is not None and face_mse > 2200:
        passed = False
        flags.append("face_region_overbake")
    if lower_mse > 12 and upper_mse > lower_mse * 8:
        # upper changed a lot while lower also moved — suspicious full redraw
        if lower_mse > 20:
            passed = False
            flags.append("global_redraw_suspect")

    return {
        "ok": True,
        "pass": passed,
        "metrics": {
            "lower_mse": round(lower_mse, 2),
            "upper_mse": round(upper_mse, 2),
            "face_mse": None if face_mse is None else round(face_mse, 2),
            "y_cut": y_cut,
        },
        "flags": flags,
        "criteria_note": (
            "FAIL when lower_half_drift — top looks refined but bottom no longer matches source"
        ),
    }


def _pick_review_model(cfg: dict[str, Any], model: str = "") -> str:
    if model.strip():
        return model.strip()
    ncfg = _nari_cfg(cfg)
    # Face review sends images — chat-only tags (nari) return HTTP 500.
    if ncfg.get("review_model"):
        return str(ncfg["review_model"]).strip()
    raw = ncfg.get("vision_models") or ncfg.get("vision_model")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, list) and raw:
        return str(raw[0]).strip()
    # Default vision tag on ComfyBox (nari:latest has no vision capability)
    return "qwen3.8:27b"


def nari_review_face_refine(
    cfg: dict[str, Any],
    *,
    before_path: str | Path,
    after_path: str | Path,
    face_prompt: str = "",
    model: str = "",
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Ask Nari (Ollama) to pass/fail a face refine with short criteria."""
    before = Path(before_path)
    after = Path(after_path)
    if not before.is_file() or not after.is_file():
        return {"ok": False, "pass": False, "error": "before/after image missing"}

    base = ollama_base_url(cfg)
    tag = _pick_review_model(cfg, model)
    user_text = (
        "BEFORE = original still. AFTER = Forge face refine candidate.\n"
        f"Requested face expression/prompt: {face_prompt or '(none — keep expression)'}\n"
        "Judge with the criteria. JSON only."
    )
    body = {
        "model": tag,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": NARI_FACE_CRITERIA},
            {
                "role": "user",
                "content": user_text,
                "images": [_b64_file(before), _b64_file(after)],
            },
        ],
    }
    try:
        r = requests.post(f"{base}/api/chat", json=body, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        content = ((data.get("message") or {}).get("content") or "").strip()
    except requests.RequestException as exc:
        return {
            "ok": False,
            "pass": False,
            "error": f"Nari review call failed: {exc}",
            "model": tag,
            "host": base,
        }

    parsed: dict[str, Any] | None = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = None

    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "pass": False,
            "error": "Nari did not return parseable JSON",
            "raw": content[:2000],
            "model": tag,
        }

    return {
        "ok": True,
        "pass": bool(parsed.get("pass")),
        "score": parsed.get("score"),
        "reasons": parsed.get("reasons") or [],
        "summary": parsed.get("summary") or "",
        "model": tag,
        "host": base,
        "raw": content[:2000],
    }


def review_face_forge(
    cfg: dict[str, Any],
    *,
    before_path: str,
    after_path: str,
    face_prompt: str = "",
    box: list[int] | None = None,
    model: str = "",
) -> dict[str, Any]:
    """Combined heuristic + Nari review (no generation)."""
    heur = heuristic_face_gate(before_path, after_path, box=box)
    nari = nari_review_face_refine(
        cfg,
        before_path=before_path,
        after_path=after_path,
        face_prompt=face_prompt,
        model=model,
    )
    # Both must pass when Nari is ok; if Nari down, heuristic alone gates soft-fail
    if nari.get("ok"):
        passed = bool(heur.get("pass")) and bool(nari.get("pass"))
    else:
        passed = bool(heur.get("pass"))
    return {
        "ok": True,
        "pass": passed,
        "heuristic": heur,
        "nari_review": nari,
        "send_to_user": passed,
        "advice": (
            "PASS — show after path to human for final keep."
            if passed
            else "FAIL — do not present as keeper; retry tighter box / lower denoise or revert."
        ),
    }


def refine_face_forge(
    cfg: dict[str, Any],
    *,
    image_path: str,
    face_prompt: str,
    negative_prompt: str = "",
    preset: str = "face_refine",
    denoise: float | None = None,
    box: list[int] | None = None,
    face_index: int = 0,
    max_attempts: int = 2,
    seed: int = -1,
    review_model: str = "",
    skip_nari: bool = False,
) -> dict[str, Any]:
    """Detect/box face → Forge region refine → Nari+heuristic review → retry loop."""
    err = _ensure_forge(cfg)
    if err:
        return err

    src = Path(image_path)
    if not src.is_file():
        return {"ok": False, "error": f"image not found: {image_path}"}

    spec = _resolve_preset(preset, denoise)
    # Build face prompt — lock identity colors + expression
    prompt = (face_prompt or "").strip()
    if not prompt:
        prompt = "same character face, keep identity, natural skin, sharp eyes"
    pl = prompt.lower()
    if "eye" not in pl and "iris" not in pl:
        prompt = f"{prompt}, keep exact eye color from source"
    if "hair" not in pl:
        prompt = f"{prompt}, keep exact hair color from source"
    if not any(
        w in pl
        for w in (
            "tattoo",
            "marking",
            "markings",
            "freckle",
            "scar",
            "glyph",
            "face paint",
            "facial mark",
        )
    ):
        prompt = f"{prompt}, keep exact face tattoos and markings from source (or none if none)"
    if "expression" not in pl and not any(
        w in pl for w in ("mouth", "smile", "smirk", "gasp", "tongue", "blush", "open", "closed")
    ):
        prompt = f"{prompt}, keep the same facial expression"

    attempts: list[dict[str, Any]] = []
    current_denoise = float(spec["denoise"])
    current_pad_frac = float(spec.get("pad_frac") or 0.08)
    last_box: list[int] | None = list(box) if box and len(box) == 4 else None

    for attempt in range(1, max(1, int(max_attempts)) + 1):
        if last_box is None:
            det = detect_face_box(src, face_index=face_index, pad_frac=current_pad_frac)
            if not det.get("ok"):
                return det
            last_box = list(det["box"])
            detect_meta = det
        else:
            detect_meta = {"ok": True, "box": last_box, "method": "provided"}

        # On retry: tighten pad and drop denoise slightly
        if attempt > 1:
            current_denoise = max(0.06, current_denoise - 0.03)
            current_pad_frac = max(0.04, current_pad_frac - 0.02)
            det2 = detect_face_box(src, face_index=face_index, pad_frac=current_pad_frac)
            if det2.get("ok"):
                last_box = list(det2["box"])
                detect_meta = det2

        gen = region_face_inpaint(
            cfg,
            image_path=src,
            box=tuple(last_box),  # type: ignore[arg-type]
            prompt=prompt,
            negative_prompt=negative_prompt,
            denoise=current_denoise,
            seed=seed if seed >= 0 else -1,
            padding=int(spec.get("padding") or 64),
        )
        if not gen.get("ok"):
            attempts.append({"attempt": attempt, "generate": gen, "pass": False})
            continue

        after = (gen.get("saved_files") or [None])[0]
        heur = heuristic_face_gate(src, after, box=last_box)
        if skip_nari:
            nari: dict[str, Any] = {"ok": True, "pass": True, "skipped": True}
        else:
            nari = nari_review_face_refine(
                cfg,
                before_path=src,
                after_path=after,
                face_prompt=prompt,
                model=review_model,
            )

        if nari.get("ok"):
            passed = bool(heur.get("pass")) and bool(nari.get("pass"))
        else:
            # Nari unavailable: heuristic only; mark needs_human if heur pass
            passed = bool(heur.get("pass"))

        attempt_rec = {
            "attempt": attempt,
            "detect": detect_meta,
            "generate": {
                "saved_files": gen.get("saved_files"),
                "frame_preview": gen.get("frame_preview"),
                "mask_path": gen.get("mask_path"),
                "denoising_strength": gen.get("denoising_strength"),
                "box": gen.get("box"),
            },
            "heuristic": heur,
            "nari_review": nari,
            "pass": passed,
        }
        attempts.append(attempt_rec)

        if passed:
            return {
                "ok": True,
                "pass": True,
                "send_to_user": True,
                "preset": spec.get("preset"),
                "denoise_guide": FACE_DENOISE_PRESETS.get(spec.get("preset") or "", {}),
                "source": str(src),
                "saved_files": gen.get("saved_files"),
                "frame_preview": gen.get("frame_preview"),
                "mask_path": gen.get("mask_path"),
                "box": gen.get("box"),
                "denoising_strength": gen.get("denoising_strength"),
                "face_prompt": prompt,
                "nari_review": nari,
                "heuristic": heur,
                "attempts": attempts,
                "advice": (
                    "Nari+heuristic PASS. Show saved_files[0] (and frame_preview) to the human. "
                    "Do not claim keeper until they approve."
                ),
            }

    best = attempts[-1] if attempts else {}
    return {
        "ok": True,
        "pass": False,
        "send_to_user": False,
        "preset": spec.get("preset"),
        "source": str(src),
        "saved_files": (best.get("generate") or {}).get("saved_files") or [],
        "frame_preview": (best.get("generate") or {}).get("frame_preview"),
        "attempts": attempts,
        "advice": (
            "FAIL after review loop — revert to original. "
            "Tighten box, lower denoise (eyes_only / face_soft), or fix expression prompt. "
            "Do not send failed after-image to the user as a keeper."
        ),
        "nari_review": best.get("nari_review"),
        "heuristic": best.get("heuristic"),
    }
