"""Queue gold-standard Frieren sex-scene redos (pose/scene locked in prompt).

Keeps character=Frieren and named pose/scene; bumps detail via gold_standard.
Run on Pi:

  PYTHONPATH=~/studio-edge ~/studio-edge-venv/bin/python \\
    -m studio_edge.gold_frieren_scenes_live
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from studio_edge import generate as gen_mod  # noqa: E402

# Pose/scene locked briefs — recreate_003 gold bar, same character
SCENES = [
    (
        "stage1_tease",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, long hair, "
        "bedroom soft daylight, standing tease, looking at viewer, "
        "partially clothed, intimate atmosphere, keep this exact pose and room layout",
    ),
    (
        "stage2_tease",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "bedroom, more undressed than stage1, same room and camera angle, "
        "same standing pose family, soft daylight",
    ),
    (
        "cowgirl",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "cowgirl sex, straddling, on bed, looking at viewer, "
        "keep exact cowgirl pose and bedroom scene, explicit",
    ),
    (
        "missionary",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "missionary sex, on back on bed, legs open, looking at partner, "
        "keep exact missionary pose and bedroom scene, explicit",
    ),
    (
        "doggystyle",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "doggystyle sex, on bed, looking back, "
        "keep exact rear pose and bedroom scene, explicit",
    ),
    (
        "oral",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "oral sex, on knees, looking up, bedroom, "
        "keep exact oral pose and scene, explicit",
    ),
    (
        "night_beach_naked",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "night beach, moonlight, wet sand, standing at waterline, naked, "
        "ocean behind, soft rim light, keep exact standing beach pose",
    ),
    (
        "night_beach_red_dress",
        "nb_frieren, Frieren, 1girl, elf, white hair, green eyes, "
        "night beach, moonlight, wet sand, standing at waterline, "
        "deep red dress wet fabric, ocean behind, keep exact standing beach pose",
    ),
]


class _NullBrain:
    api_mode = "chat"
    timeout_s = 30

    def instruct(self, directive: str, allow_chat_fallback: bool = True) -> str:
        return directive.replace("Scene: ", "")[:500]


def main() -> int:
    cfg = {
        "generation": {
            "route": "comfyui",
            "comfyui_url": "http://192.168.50.57:8188",
            "default_checkpoint": "waiIllustriousSDXL_v160.safetensors",
            "waijfu_checkpoint": "waiIllustriousSDXL_v160.safetensors",
            "expand_prompt": False,
            "deliver_to_orla": True,
            "width": 832,
            "height": 1216,
            "steps": 28,
            "cfg": 6.0,
            "timeout_s": 360,
            "default_negative": (
                "lowres, bad anatomy, worst quality, watermark, signature, "
                "wrong character, different face"
            ),
        },
        "orla": {"tools_url": "http://192.168.50.42:11436", "enabled": True},
    }
    brain = _NullBrain()
    fails = 0
    for key, scene in SCENES:
        desc = f"gold standard. Character=Frieren. {scene}"
        print(f"QUEUE {key}...")
        reply = gen_mod.generate(
            brain,
            desc,
            cfg,
            require_scene=True,
            scene_hint=scene,
            locks=["pose", "scene"],
            require_cast=True,
            quality="gold_standard",
        )
        print(f"  → {reply}")
        if any(x in reply.lower() for x in ("can't reach", "rejected", "won't", "couldn't")):
            fails += 1
    print("FAILS", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
