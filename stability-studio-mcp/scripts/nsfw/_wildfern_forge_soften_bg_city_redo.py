"""Redo every still in Wild Fern forge_soften with locked town loft BG.

Movie_* soften files only have soften-pass metadata — rebuild act layer from
beat + composition. Facesit keeps its PNG prompt act layer.

BG lock: dark brown wood panels, white sheets, headboard RIGHT, night CITY
skyline in window (town — not trees/woods). One shared seed for all jobs.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
SRC = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften"
)
OUT = SRC / "_bgcity_redo"
CKPT = "waijfu_alpha.safetensors"
SEED = 62847  # one new seed for every redo

QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)

# Locked kiss-loft BG + town window + headboard right
BG = (
    "loft bedroom at night in town, warm dark brown vertical wood panel walls, "
    "wood grain planks, dark grooves between planks, "
    "cream conical lampshade with warm yellow glow, dark ornate lamp base on dark wood nightstand, "
    "small dark framed picture on wall, "
    "wooden window showing night city skyline with lit skyscraper windows, distant city lights, "
    "no trees, urban night view, "
    "white rumpled bed sheets, white pillows, "
    "dark wood bed headboard on the right of the frame, "
    "warm low key lamp light, soft shadows, "
)

NEG = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "purple walls, lavender walls, pink walls, pale wood, magenta walls, "
    "pine trees, trees outside window, forest, evergreen, woods, rural, cabin, "
    "mountain, countryside, "
    "purple sheets, lavender sheets, pink sheets, blue sheets, "
    "cum, semen, male cum, white stains, white splatters, bukkake, aftersex, "
    "fluids, fluid, "
    "camera, dslr, camcorder, lens, smartphone, daytime, neon"
)

AD_OFF = {"ADetailer": {"args": [False]}}
AD_FACE = {
    "ADetailer": {
        "args": [
            {
                "ad_model": "face_yolov8n.pt",
                "ad_prompt": (
                    "anime face, soft diffuse catchlights, detailed iris, "
                    "round pupils, clean eyes, soft lighting, natural skin"
                ),
                "ad_negative_prompt": (
                    "lens flare, eye flare, bright catchlights, sparkle eyes, "
                    "glowing eyes, starburst, star pupils, overexposed eyes"
                ),
                "ad_confidence": 0.25,
                "ad_dilate_erode": 4,
                "ad_mask_blur": 4,
                "ad_denoising_strength": 0.3,
                "ad_inpaint_only_masked": True,
                "ad_inpaint_padding": 32,
            }
        ]
    }
}


def strip_loras(prompt: str) -> str:
    return re.sub(r"<lora:[^>]+>\s*", "", prompt).strip()


def parse_facesit_act(parameters: str) -> tuple[str, str, float]:
    """Return (act_positive, neg_extra, facesit_weight) from PNG parameters."""
    pos = parameters.split("Negative prompt:", 1)[0].strip()
    neg = ""
    if "Negative prompt:" in parameters:
        neg = parameters.split("Negative prompt:", 1)[1].split("Steps:", 1)[0].strip()
    # Drop old BG phrases; keep act after quality/style
    pos = strip_loras(pos)
    # Pull act: from facesitting / view keywords onward if present
    act = pos
    for marker in (
        "low angle looking up",
        "View from below looking up",
        "View from below",
        "facesitting",
    ):
        if marker in pos:
            act = pos[pos.index(marker) :]
            break
    # Soften weight from meta if present
    w = 0.55
    m = re.search(r"<lora:Facesitting:([0-9.]+)>", parameters)
    if m:
        w = float(m.group(1))
    return act, neg, w


def face_lora_name() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    raise RuntimeError(f"no Facesitting LoRA in {sorted(names)[:40]}")


def jobs() -> list[dict]:
    """Build one job per PNG currently in forge_soften (not subfolders)."""
    face = face_lora_name()
    out: list[dict] = []
    for path in sorted(SRC.glob("*.png")):
        name = path.stem
        with Image.open(path) as im:
            w, h = im.size
            params = im.info.get("parameters") or ""

        if name.startswith("facesit"):
            act, neg_extra, fw = parse_facesit_act(params)
            prompt = (
                f"<lora:{face}:{fw}> <lora:Fern_id_v1:0.9> "
                + QUALITY
                + BG
                + act
            )
            neg = NEG + (
                ", man, male, penis, cock, 1boy, "
                "blonde on top, blue eyes on Fern, purple eyes under, "
                "purple bangs under, black hair under, two Ferns, "
                "closed eyes, eyes closed, clothes, lingerie, pubic hair, "
                "small breasts, flat chest"
            )
            if neg_extra:
                # keep eye-role locks from meta if any unique bits
                for bit in (
                    "blonde on top",
                    "blue eyes on Fern",
                    "purple eyes under",
                    "two Ferns",
                    "closed eyes",
                ):
                    if bit in neg_extra and bit not in neg:
                        neg += f", {bit}"
            out.append(
                dict(
                    name=name,
                    src=path,
                    prompt=prompt,
                    neg=neg,
                    w=w,
                    h=h,
                    mode="txt2img",
                    denoise=None,
                    ad=False,
                )
            )
            continue

        # Movie stills — act by stem (soften meta is useless)
        if "kiss" in name:
            act = (
                "side view close-up, 2girls, nb_fern, Fern, long purple hair, purple eyes, "
                "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
                "both completely nude, large breasts, kissing, french kiss, tongues touching, "
                "Darkness leaning over Fern on the bed, intimate embrace, "
                "yuri, lesbian"
            )
            lora = "<lora:Fern_id_v1:0.85> <lora:Darkness_id_v1:0.85> "
            ad = True
        elif "fern_licks" in name:
            act = (
                "View from mans POV looking up, solo focus, 1girl, nb_fern, Fern, "
                "long purple hair in ponytail, purple eyes, completely nude, large breasts, "
                "leaning over viewer, face near crotch, tongue out licking pussy, cunnilingus, "
                "blonde hands cupping breasts at bottom of frame, wet pussy"
            )
            lora = f"<lora:{face}:0.35> <lora:Fern_id_v1:0.9> "
            ad = True
        elif "revcowgirl" in name:
            act = (
                "View from below looking up, reverse cowgirl, ass focus, solo focus, 1girl, "
                "nb_fern, Fern, long purple hair down bare back, completely nude, "
                "large breasts, bare ass, riding strap-on, purple strap-on harness, "
                "straddling viewer, hands on thighs at bottom of frame, "
                "head facing away toward window, no lookback, wet pussy"
            )
            lora = "<lora:Fern_id_v1:0.9> "
            ad = False
        elif "doggy" in name:
            act = (
                "from behind, doggystyle, 2girls, nb_fern, Fern, long purple hair, purple eyes, "
                "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
                "Fern fucking Darkness from behind with strap-on, purple strap-on, "
                "Darkness on hands and knees on bed, looking back over shoulder, "
                "both completely nude, large breasts, vaginal penetration, yuri, lesbian"
            )
            lora = "<lora:Fern_id_v1:0.85> <lora:Darkness_id_v1:0.85> "
            ad = True
        elif "aftercare" in name:
            act = (
                "high angle view looking down, 2girls, nb_fern, Fern, long purple hair, purple eyes, "
                "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
                "both completely nude, large breasts, lying in bed together after sex, "
                "Darkness resting head on Ferns chest, soft aftercare, sweaty skin, tired, "
                "intimate, yuri, lesbian, no sex act"
            )
            lora = "<lora:Fern_id_v1:0.85> <lora:Darkness_id_v1:0.85> "
            ad = True
        else:
            print("SKIP unknown", name, flush=True)
            continue

        prompt = lora + QUALITY + BG + act
        neg = NEG + ", man, male, penis, cock, 1boy, clothes, lingerie, pubic hair"
        out.append(
            dict(
                name=name,
                src=path,
                prompt=prompt,
                neg=neg,
                w=w,
                h=h,
                mode="img2img",
                denoise=0.52,
                ad=ad,
            )
        )
    return out


def run_txt2img(job: dict) -> Path:
    payload = {
        "prompt": job["prompt"],
        "negative_prompt": job["neg"],
        "steps": 32,
        "cfg_scale": 6.0,
        "width": job["w"],
        "height": job["h"],
        "seed": SEED,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF if not job["ad"] else AD_FACE,
    }
    r = requests.post(f"{FORGE}/sdapi/v1/txt2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    dest = OUT / f"{job['name']}_bgcity.png"
    dest.write_bytes(raw)
    return dest


def run_img2img(job: dict) -> Path:
    tmp = OUT / "_rgb"
    tmp.mkdir(parents=True, exist_ok=True)
    rgb = tmp / f"{job['src'].stem}.png"
    with Image.open(job["src"]) as im:
        im.convert("RGB").save(rgb, format="PNG")
    payload = {
        "init_images": [base64.b64encode(rgb.read_bytes()).decode()],
        "prompt": job["prompt"],
        "negative_prompt": job["neg"],
        "denoising_strength": job["denoise"],
        "steps": 32,
        "cfg_scale": 6.0,
        "width": job["w"],
        "height": job["h"],
        "seed": SEED,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF if not job["ad"] else AD_FACE,
    }
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    dest = OUT / f"{job['name']}_bgcity.png"
    dest.write_bytes(raw)
    return dest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    all_jobs = jobs()
    print(f"SEED={SEED} jobs={len(all_jobs)} out={OUT}", flush=True)
    results = []
    for i, job in enumerate(all_jobs, 1):
        print(
            f"[{i}/{len(all_jobs)}] {job['mode']} {job['name']} "
            f"{job['w']}x{job['h']} d={job['denoise']}",
            flush=True,
        )
        try:
            if job["mode"] == "txt2img":
                dest = run_txt2img(job)
            else:
                dest = run_img2img(job)
            meta = {
                "name": job["name"],
                "seed": SEED,
                "mode": job["mode"],
                "denoise": job["denoise"],
                "src": str(job["src"]),
                "out": str(dest),
                "prompt": job["prompt"],
                "negative": job["neg"],
            }
            (OUT / f"{job['name']}_bgcity.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )
            print("  OK", dest.name, dest.stat().st_size, flush=True)
            results.append({"name": job["name"], "ok": True, "path": str(dest)})
        except Exception as e:
            print("  FAIL", e, flush=True)
            results.append({"name": job["name"], "ok": False, "error": str(e)})

    (OUT / "_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok = sum(1 for x in results if x.get("ok"))
    print(f"DONE {ok}/{len(results)} seed={SEED}", flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
