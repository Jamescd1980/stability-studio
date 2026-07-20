"""Smoke thin-Myra routing + cast aliases + brief (no GPU required for most checks)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from studio_edge import cast_resolve  # noqa: E402
from studio_edge import generate as gen_mod  # noqa: E402
from studio_edge import image_brief  # noqa: E402
from studio_edge.intents import classify  # noqa: E402


def main() -> int:
    fails = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal fails
        if cond:
            print(f"OK  {name}")
        else:
            fails += 1
            print(f"FAIL {name} {detail}")

    # Intents
    check("web_lookup", classify("look this up for me Denver population").kind == "web_lookup")
    check("image_brief", classify("make an image of Ubel on the beach").kind == "image_brief")
    check("ask_nari_create", classify("ask Nari to make an image of Fern").kind == "image_brief")
    check("recreate", classify("recreate that image but make her naked").kind == "recreate")
    check("cast_swap", classify("keep the pose and change the character to Fern").kind == "cast_swap")
    check(
        "same_scene_not_swap",
        classify("The same scene is the original fucking image.").kind != "cast_swap",
    )
    check("recreate_hyphen", classify("I need re-create an image using studio edge 3").kind == "recreate")
    check("cast_batch", classify("one of each from Frieren").kind == "cast_batch")
    check("orla_display", classify("have Orla display the newest image").kind == "ask_orla")
    check("conversation_no_gofor_trap", classify("hello there").kind == "conversation")

    # STT / cast
    fixed = gen_mod.correct_stt_names("He-jin Park standing")
    check("stt heejin", "Heejin" in fixed or "heejin" in fixed.lower(), fixed)
    frieren_stt = gen_mod.correct_stt_names(
        "character is a frayer in. She has silver hair"
    )
    check("stt frieren", "Frieren" in frieren_stt, frieren_stt)
    check("cast heejin", cast_resolve.match_character("Hijing Park") is not None)
    check("cast ubele", (cast_resolve.match_character("Ubele") or {}).get("id") == "ubel")
    check(
        "no_cha_on_character",
        cast_resolve.match_character("character is a frayer in") is None
        or (cast_resolve.match_character(
            gen_mod.correct_stt_names("character is a frayer in")
        ) or {}).get("id") == "frieren",
    )
    check(
        "no_gina_in_original",
        cast_resolve.match_character("same as the original image") is None,
    )
    check(
        "no_cha_on_change",
        cast_resolve.match_character("Change character to Ferry") is None
        or (cast_resolve.match_character(
            gen_mod.correct_stt_names("Change character to Ferry")
        ) or {}).get("id") == "frieren",
    )
    frieren = cast_resolve.characters_for_show("frieren")
    check("frieren cast", len(frieren) >= 3, str(frieren))
    check(
        "studio_agent_spoken",
        image_brief._parse_studio_edge(  # noqa: SLF001
            "studio agent zero three"
        )
        == "studio_agent_00003",
    )
    check(
        "studio_agent_00031",
        image_brief._parse_studio_edge("studio agent 00031") == "studio_agent_00031",
    )
    check(
        "studio_edge_spoken_maps_agent",
        image_brief._parse_studio_edge("studio edge 9") == "studio_agent_00009",
    )
    check(
        "studio_agent_reject_0000",
        image_brief._parse_studio_edge("studio agent 0000") is None,
    )
    check(
        "studio_agent_spoken_seq",
        image_brief._parse_studio_edge("zero zero zero three one") == "studio_agent_00031",
    )
    # Wrong image / abort
    image_brief.clear()
    image_brief.start("recreate studio agent 0000")
    b0 = image_brief.active()
    check("reject_zero_asks_source", b0 is not None and b0.slot == "source", str(b0))
    image_brief.clear()
    image_brief.start("recreate using Studio Agent 00031")
    b1 = image_brief.active()
    check(
        "source_00031",
        b1 is not None and b1.source_selector == "studio_agent_00031",
        str(getattr(b1, "source_selector", None)),
    )
    r_wrong = image_brief.feed("No. Wrong image", None, {})
    b2 = image_brief.active()
    check(
        "wrong_image_reask",
        b2 is not None and b2.slot == "source" and "studio agent" in r_wrong.lower(),
        r_wrong,
    )
    r_fix = image_brief.feed("thirty one", None, {})
    b3 = image_brief.active()
    check(
        "source_thirty_one",
        b3 is not None and b3.source_selector == "studio_agent_00031",
        str(getattr(b3, "source_selector", None)),
    )
    r_abort = image_brief.feed("Fuck you.", None, {})
    check(
        "fuck_you_abort",
        (not image_brief.is_active())
        and "sorry" in r_abort.lower()
        and "reset process" in r_abort.lower(),
        r_abort,
    )
    check("abort_latch", image_brief.consume_abort() is True)
    image_brief.clear()
    image_brief.start("recreate studio edge 31")
    r_named = image_brief.feed("Fuck you Myra", None, {})
    check(
        "fuck_you_name",
        (not image_brief.is_active()) and "sorry" in r_named.lower(),
        r_named,
    )
    image_brief.consume_abort()

    # Brief state machine
    image_brief.clear()
    q1 = image_brief.start("make an image")
    check("brief starts", image_brief.is_active() and "?" in q1, q1)
    q2 = image_brief.feed("anime", None, {})
    check("brief style", image_brief.is_active(), q2)
    q3 = image_brief.feed("Ubele", None, {})
    check("brief character", "Ubel" in (image_brief.active().character if image_brief.active() else ""), q3)
    q4 = image_brief.feed("at night on the beach", None, {})
    check("brief confirm", "yes" in q4.lower() or "Say yes" in q4, q4)
    image_brief.clear()

    print("---")
    print("FAILS", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
