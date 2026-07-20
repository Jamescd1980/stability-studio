"""STT-misspell + beach + Frieren cast + recreate sim (no GPU unless --live).

Imitates Hailo mishears, walks image_brief/cast/recreate paths, asserts
gold-standard + pose/scene locks. Run on Pi:

  PYTHONPATH=~/studio-edge ~/studio-edge-venv/bin/python \\
    -m studio_edge.smoke_stt_beach_sim
  PYTHONPATH=~/studio-edge ~/studio-edge-venv/bin/python \\
    -m studio_edge.smoke_stt_beach_sim --live
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from studio_edge import cast_resolve  # noqa: E402
from studio_edge import generate as gen_mod  # noqa: E402
from studio_edge import image_brief  # noqa: E402
from studio_edge.intents import classify  # noqa: E402

# Night beach scene the user keeps requesting
BEACH_SCENE = (
    "night beach, moonlight on wet sand, standing at the waterline, "
    "ocean behind her, soft rim light"
)

# Hailo-style mishears → expected cast id
MISHEARD_CAST = [
    ("character is a frayer in", "frieren"),
    ("Change character to Ferry.", "frieren"),
    ("free rin on the beach", "frieren"),
    ("make firm on the beach", "fern"),
    ("character named Firm", "fern"),
    ("ubele night beach", "ubel"),
    ("will you see actual character on the beach", "ubel"),
    ("o bell standing on the beach", "ubel"),
    ("flame from frieren", "flamme"),
    ("flamme beach night", "flamme"),
    ("Park He-jin on the beach", "park_heejin"),
    ("hijing park night beach", "park_heejin"),
]

CLOTHING_VARIANTS = [
    "same pose and scene, red dress",
    "same pose and scene, black bikini",
    "same pose and scene, make her naked",
    "same pose and scene, white robe open",
]

FRIEREN_CAST = ["frieren", "fern", "flamme", "ubel"]


def _load_cfg() -> dict:
    for p in (
        Path.home() / "studio-edge" / "config.yaml",
        ROOT / "config.yaml",
    ):
        if p.is_file():
            try:
                import yaml  # type: ignore

                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
    return {
        "generation": {
            "route": "comfyui",
            "comfyui_url": "http://192.168.50.57:8188",
            "expand_prompt": False,
            "deliver_to_orla": False,
            "quality_default": "gold_standard",
        },
        "orla": {"tools_url": "http://192.168.50.42:11436"},
    }


class _NullBrain:
    """Skip Nari expand in dry-run; echo description."""

    api_mode = "chat"
    timeout_s = 30

    def instruct(self, directive: str, allow_chat_fallback: bool = True) -> str:
        return directive.replace("Scene: ", "")[:400]

    def is_up(self) -> bool:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--live",
        action="store_true",
        help="Queue real Comfy jobs (gold standard beach + recreates)",
    )
    ap.add_argument("--max-live", type=int, default=8, help="Cap live Comfy jobs")
    args = ap.parse_args()
    cfg = _load_cfg()
    fails = 0
    report: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal fails
        if cond:
            print(f"OK  {name}")
            report.append(f"OK  {name}")
        else:
            fails += 1
            print(f"FAIL {name} {detail}")
            report.append(f"FAIL {name} {detail}")

    # --- STT + cast resolve ---
    for uttered, expect_id in MISHEARD_CAST:
        fixed = gen_mod.correct_stt_names(uttered)
        hit = cast_resolve.match_character(fixed) or cast_resolve.match_character(uttered)
        got = (hit or {}).get("id")
        check(f"cast:{uttered[:40]}", got == expect_id, f"got={got} fixed={fixed!r}")

    # False friends
    check(
        "no_gina_original",
        cast_resolve.match_character("same as the original image") is None,
    )
    check(
        "no_cha_on_change",
        cast_resolve.match_character("Change character please") is None,
    )
    check(
        "same_scene_not_swap",
        classify("The same scene is the original fucking image.").kind != "cast_swap",
    )
    check(
        "fuck_you_myra",
        bool(image_brief._HARD_ABORT_RE.search("Fuck you Myra")),  # noqa: SLF001
    )

    # --- Guided brief: misheard Frieren → beach → gold → clothing ---
    image_brief.clear()
    q = image_brief.start("Talk to Nari, make an image")
    check("brief_start", image_brief.is_active() and "?" in q, q)
    image_brief.feed("wageful", None, cfg)
    image_brief.feed("character is a frayer in. silver hair", None, cfg)
    b = image_brief.active()
    check("brief_frieren", b is not None and b.character == "Frieren", str(b))
    image_brief.feed(BEACH_SCENE, None, cfg)
    image_brief.feed("gold standard quality, absurdres", None, cfg)
    b = image_brief.active()
    check(
        "brief_gold",
        b is not None
        and (
            getattr(b, "quality", "") == "gold_standard"
            or "gold" in (b.extras or "").lower()
            or "gold" in (b.scene or "").lower()
            or "gold" in (b.style or "").lower()
        ),
        str(b),
    )
    # clothing / naked variants at confirm
    for cloth in CLOTHING_VARIANTS:
        image_brief.clear()
        image_brief.start("make an image of Frieren")
        image_brief.feed("waijfu", None, cfg)
        # character may already be seeded
        if image_brief.active() and not image_brief.active().character:
            image_brief.feed("Frieren", None, cfg)
        if image_brief.active() and image_brief.active().slot == "scene":
            image_brief.feed(BEACH_SCENE, None, cfg)
        r = image_brief.feed(cloth, None, cfg)
        b = image_brief.active()
        ok = b is not None and (
            "naked" in cloth
            and ("naked" in (b.scene or "").lower() or "naked" in (b.extras or "").lower()
                 or "nude" in (b.scene or "").lower() or "nude" in (b.extras or "").lower())
            or "dress" in cloth
            and ("dress" in (b.scene or "").lower() or "dress" in (b.extras or "").lower()
                 or "red" in (b.scene or "").lower() or "red" in (b.extras or "").lower())
            or "bikini" in cloth
            and ("bikini" in (b.scene or "").lower() or "bikini" in (b.extras or "").lower())
            or "robe" in cloth
            and ("robe" in (b.scene or "").lower() or "robe" in (b.extras or "").lower())
            or "Say yes" in r
            or "yes" in r.lower()
        )
        check(f"cloth:{cloth[:28]}", ok, f"scene={getattr(b,'scene',None)!r} extras={getattr(b,'extras',None)!r} r={r!r}")

    # --- Cast swap through Frieren cast (dry brief packets) ---
    for cid in FRIEREN_CAST:
        image_brief.clear()
        ch = cast_resolve._char_by_id(cast_resolve._load()[0], cid)  # noqa: SLF001
        name = (ch or {}).get("display_name") or cid
        # misheard entry then correct via change character
        uttered = {
            "frieren": "frayer in",
            "fern": "Firm",
            "flamme": "Flame",
            "ubel": "ubele",
        }[cid]
        image_brief.start(
            f"keep the pose and scene, change character to {uttered}, "
            f"night beach gold standard"
        )
        b = image_brief.active()
        check(
            f"swap_seed:{cid}",
            b is not None
            and b.mode == "cast_swap"
            and (b.character or "").lower().startswith(name[:3].lower()),
            str(b),
        )

    # --- Recreate path: reject 0000, accept 00031, wrong image, gold ---
    image_brief.clear()
    image_brief.start("recreate studio agent 0000")
    b = image_brief.active()
    check("recreate_reject_0000", b is not None and b.slot == "source", str(b))
    image_brief.feed("No. Wrong image", None, cfg)
    check("recreate_wrong", image_brief.active() is not None and image_brief.active().slot == "source")
    image_brief.feed("zero zero zero three one", None, cfg)
    b = image_brief.active()
    check(
        "recreate_31",
        b is not None and b.source_selector == "studio_agent_00031",
        str(getattr(b, "source_selector", None)),
    )
    image_brief.feed(
        "same pose and scene, gold standard, more detail, keep character",
        None,
        cfg,
    )
    b = image_brief.active()
    check(
        "recreate_locks_gold",
        b is not None
        and "pose" in (b.locks or [])
        and "scene" in (b.locks or [])
        and (
            getattr(b, "quality", "") == "gold_standard"
            or "gold" in (b.scene or "").lower()
            or "gold" in (b.extras or "").lower()
        ),
        str(b),
    )

    # Quality helper unit check
    if hasattr(gen_mod, "detect_quality"):
        qn, _ = gen_mod.detect_quality("gold standard beach frieren")
        check("detect_gold", qn == "gold_standard", str(qn))
    else:
        check("detect_gold", False, "detect_quality missing")

    # Abort
    image_brief.feed("Fuck you Nari", None, cfg)
    check("abort_named", not image_brief.is_active())
    image_brief.consume_abort()

    live_results: list[str] = []
    if args.live:
        print("--- LIVE Comfy (capped) ---")
        brain = _NullBrain()
        cfg_live = json.loads(json.dumps(cfg))
        gen = cfg_live.setdefault("generation", {})
        gen["expand_prompt"] = False
        gen["deliver_to_orla"] = True
        gen["quality_default"] = "gold_standard"
        queued = 0
        # Beach create per Frieren cast + clothing naked/red
        for cid in FRIEREN_CAST:
            if queued >= args.max_live:
                break
            ch = cast_resolve._char_by_id(cast_resolve._load()[0], cid)  # noqa: SLF001
            name = (ch or {}).get("display_name") or cid
            desc = (
                f"gold standard. {name}. {BEACH_SCENE}. "
                f"{'naked, explicit nude' if queued % 2 == 0 else 'deep red dress, wet fabric'}"
            )
            print(f"LIVE create {name}: {desc[:80]}...")
            reply = gen_mod.generate(
                brain,
                desc,
                cfg_live,
                require_scene=True,
                scene_hint=BEACH_SCENE,
                locks=[],
                require_cast=True,
            )
            live_results.append(f"{name}: {reply}")
            print(f"  → {reply}")
            queued += 1
            check(f"live_create:{cid}", "can't reach" not in reply.lower() and "rejected" not in reply.lower(), reply)

        # Recreate gold from gallery ids that exist (00031 may live under User Import)
        resolved_any = False
        for sel in ("studio_agent_00009", "studio_agent_00031", "newest"):
            if queued >= args.max_live:
                break
            src = gen_mod.resolve_source_meta(cfg_live, sel)
            if not src.get("ok"):
                print(f"SKIP resolve {sel}: {src.get('error')}")
                continue
            resolved_any = True
            print(f"LIVE recreate {sel} gold+locks → {src.get('path')}")
            reply = gen_mod.recreate_or_adjust(
                brain,
                cfg_live,
                selector=sel,
                adjust_text=(
                    "gold standard quality, highly detailed, absurdres, "
                    "keep exact character pose and scene, enhance detail only"
                ),
                locks=["pose", "scene"],
            )
            live_results.append(f"recreate {sel}: {reply}")
            print(f"  → {reply}")
            queued += 1
            check(
                f"live_recreate:{sel}",
                "couldn't find" not in reply.lower(),
                reply,
            )
        check("live_resolve_any", resolved_any, "no gallery sources resolved")

    out = ROOT / "smoke_stt_beach_sim_report.txt"
    try:
        out.write_text("\n".join(report + [""] + live_results) + f"\nFAILS {fails}\n", encoding="utf-8")
    except OSError:
        pass

    print("---")
    print("FAILS", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
