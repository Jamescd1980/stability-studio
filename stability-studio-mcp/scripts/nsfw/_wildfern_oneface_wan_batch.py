"""Wan I2V for Wild Fern one-face pack — oral then strap."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402

IMP = Path(r"D:\ComfyBox Images and Videos\User Import\WildFern_oneface")
VID = Path(r"D:\ComfyBox Images and Videos\Video\Theater Jobs\Where the Wild Fern Moans\Work")
GAME = Path(r"D:\Bad boy\TheaterJobs\game\videos\Movie_WildFern")

ORAL = [
    {
        "file": "wan2.2-i2v-high-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "high",
    },
    {
        "file": "wan2.2-i2v-low-oral-insertion-v1.0.safetensors",
        "weight": 0.7,
        "branch": "low",
    },
]
DOGGY = [
    {
        "file": "wan2.2-i2v-high-doggy-style-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "high",
    },
    {
        "file": "wan2.2-i2v-low-doggy-style-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "low",
    },
]
MISSIONARY = [
    {
        "file": "wan2.2-i2v-high-missionary-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "high",
    },
    {
        "file": "wan2.2-i2v-low-missionary-sex-14b.safetensors",
        "weight": 0.55,
        "branch": "low",
    },
]

JOBS = [
    dict(
        id="fern_licks",
        stem="darkness_on_top",
        image=IMP / "WF01_fern_licks_wanstart.png",
        frames=33,
        loras=ORAL,
        prompt="nsfw, she is giving her a licking, tongue licks gently up and down on her pussy, lips stay on the pussy",
        neg=(
            "pulling away, empty mouth, second face, two faces, man, male, penis, "
            "head shake, melting face, morphing face, camera, dslr"
        ),
    ),
    dict(
        id="facesit",
        stem="fern_on_top",
        image=IMP / "WF02_facesit_wanstart.png",
        frames=33,
        loras=ORAL,
        prompt="nsfw, she is getting her pussy licked, soft tongue motion, head stays buried, lips stay on the pussy",
        neg=(
            "pulling away, empty mouth, second face, two faces, blonde face, man, male, penis, "
            "melting face, morphing face, camera, dslr"
        ),
    ),
    dict(
        id="darkness_strap",
        stem="darkness_doggy",
        image=IMP / "WF03_lookback_wanstart.png",
        frames=21,
        loras=DOGGY,
        prompt="doggy style sex, short front-to-back hip thrust, strap stays inside",
        neg=(
            "full withdrawal, penis exit, second face, two faces, looking at each other, "
            "melting face, morphing face, camera, dslr, man face"
        ),
    ),
    dict(
        id="fern_strap",
        stem="fern_doggy",
        image=IMP / "WF04_missionary_wanstart.png",
        frames=21,
        loras=MISSIONARY,
        prompt="missionary sex, short front-to-back thrusts, partial withdraw only, strap stays inside",
        neg=(
            "full withdrawal, penis exit, second face, two faces, melting face, morphing face, "
            "camera, dslr"
        ),
    ),
]


def main() -> int:
    VID.mkdir(parents=True, exist_ok=True)
    GAME.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    results = []
    for j in JOBS:
        print("=== WAN", j["id"], j["frames"], flush=True)
        if not j["image"].is_file():
            print("MISSING", j["image"], flush=True)
            results.append({"id": j["id"], "ok": False, "error": "missing still"})
            continue
        try:
            r = eng.generate_video(
                prompt=j["prompt"],
                mode="i2v",
                workflow_id="i2v",
                negative_prompt=j["neg"],
                image_path=str(j["image"]),
                num_frames=j["frames"],
                frame_rate=16.0,
                loras=j["loras"],
                moe_preset="quality",
                draft=False,
                content_rating="open",
            )
            # apply weights via second path if engine ignored — check result
            saved = r.get("saved_files") or []
            mp4 = next((Path(p) for p in saved if str(p).lower().endswith(".mp4")), None)
            if not mp4 or not mp4.is_file():
                print("FAIL no mp4", r, flush=True)
                results.append({"id": j["id"], "ok": False, "raw": r})
                continue
            dest = VID / f"WF_{j['id']}_{mp4.stem}.mp4"
            shutil.copy2(mp4, dest)
            game_dest = GAME / f"{j['stem']}.mp4"
            shutil.copy2(mp4, game_dest)
            print("OK", dest, "->", game_dest, flush=True)
            results.append(
                {
                    "id": j["id"],
                    "ok": True,
                    "work": str(dest),
                    "game": str(game_dest),
                    "source": str(mp4),
                }
            )
        except Exception as e:
            print("ERR", j["id"], e, flush=True)
            results.append({"id": j["id"], "ok": False, "error": str(e)})
    out = VID / "_wan_batch.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0 if all(x.get("ok") for x in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
