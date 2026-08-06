"""Wild Fern BG city — img2img from ORIGINAL square keepers (not Ren'Py pads).

No ControlNet. Raster = original. Denoise ladder 0.30 / 0.40 / 0.50, 3 each.
Shared seed. Locked town loft BG (city skyline, wood walls, white sheets, headboard right).
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\_bgcity_i2i"
)
CKPT = "waijfu_alpha.safetensors"
SEED = 62847
DENOISES = (0.30, 0.40, 0.50)

STILLS = Path(r"D:\ComfyBox Images and Videos\Images\Theater Jobs\Where the Wild Fern Moans\Stills")
APPROVED = STILLS / "Approved"
REVIEW = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\review"
)

# Original keepers (square) — NOT game/cg Ren'Py blurred letterbox pads
SOURCES = [
    dict(
        id="01_kiss",
        src=STILLS / "FD_kissing_KEEP.png",
        act=(
            "side view close-up, 2girls, nb_fern, Fern, long purple hair, purple eyes, "
            "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "both completely nude, kissing, french kiss, tongues touching, yuri"
        ),
        ad=True,
    ),
    dict(
        id="02_fern_licks",
        src=STILLS / "FD_fern_licks_darkness_KEEP.png",
        act=(
            "1girl, nb_fern, Fern, long purple hair, purple eyes, completely nude, "
            "face between thighs, tongue licking pussy, cunnilingus, wet pussy"
        ),
        ad=True,
    ),
    dict(
        id="04_fern_revcowgirl",
        src=REVIEW / "fern_revcowgirl_v1.png",
        act=(
            "1girl, nb_fern, Fern, long purple hair, reverse cowgirl, ass focus, "
            "completely nude, riding strap-on, purple strap-on, wet pussy"
        ),
        ad=False,
    ),
    dict(
        id="05_fern_doggy",
        src=APPROVED / "fern_doggy_v1.png",
        act=(
            "2girls, nb_fern, Fern, long purple hair, purple eyes, "
            "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "doggystyle, Fern fucking Darkness from behind with strap-on, "
            "both completely nude, vaginal penetration, yuri"
        ),
        ad=True,
    ),
    dict(
        id="06_aftercare",
        src=APPROVED / "Aftercare_v2.png",
        act=(
            "2girls, nb_fern, Fern, long purple hair, purple eyes, "
            "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "both completely nude, lying in bed together, aftercare, soft, no sex act, yuri"
        ),
        ad=True,
    ),
    dict(
        id="facesit_darkness_pov_v3",
        src=STILLS / "forge_soften" / "facesit_darkness_pov_v3.png",
        act=(
            "low angle looking up, facesitting, solo focus, 1girl, nb_fern, Fern, "
            "purple hair, purple eyes, completely nude, large breasts, pussy on face, "
            "looking down at viewer, blonde bangs, blue eyes looking up at bottom edge, "
            "wet pussy, cunnilingus"
        ),
        ad=False,
        lora_extra="<lora:Facesitting:0.55> ",
    ),
]

QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)
BG = (
    "loft bedroom at night in town, warm dark brown vertical wood panel walls, "
    "wood grain planks, dark grooves between planks, "
    "cream conical lampshade with warm yellow glow, dark ornate lamp base on dark wood nightstand, "
    "small dark framed picture on wall, "
    "wooden window showing night city skyline with lit skyscrapers, distant city lights, "
    "urban night view, no trees, "
    "white rumpled bed sheets, white pillows, "
    "dark wood bed headboard on the right of the frame, "
    "warm low key lamp light, soft shadows, "
)
NEG = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "purple walls, lavender walls, pink walls, pale wood, yellow walls, "
    "pine trees, trees outside window, forest, evergreen, woods, rural, cabin, "
    "purple sheets, lavender sheets, pink sheets, "
    "cum, semen, white stains, white splatters, bukkake, aftersex, fluids, fluid, "
    "camera, dslr, camcorder, daytime, neon, "
    "man, male, penis, cock, 1boy, clothes, lingerie, pubic hair"
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
                    "glowing eyes, starburst, star pupils"
                ),
                "ad_confidence": 0.25,
                "ad_dilate_erode": 4,
                "ad_mask_blur": 4,
                "ad_denoising_strength": 0.28,
                "ad_inpaint_only_masked": True,
                "ad_inpaint_padding": 32,
            }
        ]
    }
}


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    return "Facesitting"


def build_prompt(job: dict, face: str) -> str:
    extra = job.get("lora_extra", "")
    if "Facesitting" in extra:
        extra = extra.replace("Facesitting", face)
    # Character LoRAs — facesit: Fern only (Darkness ID flips seat)
    if job["id"].startswith("facesit") or job["id"] in ("02_fern_licks", "04_fern_revcowgirl"):
        lora = f"{extra}<lora:Fern_id_v1:0.9> "
    else:
        lora = f"<lora:Fern_id_v1:0.85> <lora:Darkness_id_v1:0.85> "
    return lora + QUALITY + BG + job["act"]


def img2img(*, name: str, src: Path, prompt: str, denoise: float, ad: bool) -> Path:
    with Image.open(src) as im:
        w, h = im.size
        rgb = im.convert("RGB")
    tmp = OUT / "_rgb"
    tmp.mkdir(parents=True, exist_ok=True)
    rgb_path = tmp / f"{src.stem}.png"
    rgb.save(rgb_path, format="PNG")

    dest = OUT / f"{name}_d{int(denoise * 100):02d}.png"
    payload = {
        "init_images": [base64.b64encode(rgb_path.read_bytes()).decode()],
        "prompt": prompt,
        "negative_prompt": NEG,
        "denoising_strength": denoise,
        "steps": 32,
        "cfg_scale": 6.0,
        "width": w,
        "height": h,
        "seed": SEED,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_FACE if ad else AD_OFF,
    }
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    dest.write_bytes(raw)
    (OUT / f"{dest.stem}.json").write_text(
        json.dumps(
            {
                "name": name,
                "src": str(src),
                "seed": SEED,
                "denoise": denoise,
                "prompt": prompt,
                "out": str(dest),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return dest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for job in SOURCES:
        if not job["src"].is_file():
            raise FileNotFoundError(job["src"])
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    jobs = []
    for job in SOURCES:
        prompt = build_prompt(job, face)
        for d in DENOISES:
            jobs.append((job, prompt, d))

    print(f"SEED={SEED} jobs={len(jobs)} (no ControlNet) out={OUT}", flush=True)
    results = []
    for i, (job, prompt, d) in enumerate(jobs, 1):
        tag = f"{job['id']}_d{int(d * 100):02d}"
        print(f"[{i}/{len(jobs)}] i2i {tag} <- {job['src'].name} d={d}", flush=True)
        try:
            dest = img2img(
                name=job["id"],
                src=job["src"],
                prompt=prompt,
                denoise=d,
                ad=job["ad"],
            )
            print("  OK", dest.name, dest.stat().st_size, flush=True)
            results.append({"name": tag, "ok": True, "path": str(dest)})
        except Exception as e:
            print("  FAIL", e, flush=True)
            results.append({"name": tag, "ok": False, "error": str(e)})

    (OUT / "_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok = sum(1 for x in results if x.get("ok"))
    print(f"DONE {ok}/{len(results)} seed={SEED}", flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
