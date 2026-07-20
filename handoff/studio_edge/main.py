"""Studio Edge main loop: wake (Myra|Jan) -> listen -> route -> speak."""
from __future__ import annotations

import logging
import random
import re
import signal
import sys
import time

from . import audio as audio_mod
from . import generate as gen_mod
from . import image_brief
from . import intents as intents_mod
from . import notes as notes_mod
from . import pose_capture
from . import room_tools
from .brain import JanBrain
from .config import load_config
from .local_brain import LocalBrain
from .stt import build_transcriber
from .tts import Speaker
from .wakeword import WakeWord, resolve_persona

_FOLLOW_UP_OFFER_RE = re.compile(
    r"(?:"
    r"\?"
    r"|would you like"
    r"|want(?:\s+me|\s+to know|\s+more|\s+the\s+rest)?"
    r"|shall i"
    r"|should i"
    r"|more detail"
    r"|hear more"
    r"|know more"
    r"|keep going"
    r"|continue"
    r")",
    re.I,
)
_FOLLOW_UP_END_RE = re.compile(
    r"^\s*(?:"
    r"no(?:pe)?|nah|stop|enough|cancel|never\s*mind|thats?\s+all|"
    r"that(?:'s|s)\s+all|goodbye|bye|thanks?(?:\s+you)?|i(?:'m|\s+am)\s+good"
    r")\s*[.!?]?\s*$",
    re.I,
)
# "Fuck you" / "Fuck you Myra" / "Fuck you, Nari" (any short name)
_HARD_ABORT_RE = re.compile(
    r"\b(?:fuck\s+you(?:\s*,?\s*[A-Za-z][A-Za-z']{0,20})?|"
    r"fuck\s+this|fuck\s+off|screw\s+(?:this|you)|"
    r"shut\s+(?:the\s+fuck\s+)?up|kill\s+it|abort|"
    r"god\s*damn\s+it|stop\s+everything|stop\s+all)\b",
    re.I,
)
# Hailo/Whisper noise labels — do not send to the gofor LLM.
_FOLLOW_UP_NOISE_RE = re.compile(
    r"^\s*(?:"
    r"\[?\s*blank[_\s-]?audio\s*\]?"
    r"|\[?\s*silence\s*\]?"
    r"|\[?\s*inaudible\s*\]?"
    r"|\[?\s*music\s*\]?"
    r"|\[?\s*noise\s*\]?"
    r"|\[?\s*coughing\s*\]?"
    r"|\([^)]*\)"
    r")\s*$",
    re.I,
)
# User often re-says the wake word during the follow-up window — don't LLM that.
# STT mangles: "Hey, myra." / "A. Myra?" / "Myra?"
_FOLLOW_UP_WAKE_ECHO_RE = re.compile(
    r"^\s*(?:hey[,\s]+|a[.\s]+|ok[,\s]+)?"
    r"(?:myra|mira|jan|nari|orluh|orla)\s*[!?.]*\s*$",
    re.I,
)


def build(cfg: dict):
    audio_cfg = cfg.get("audio", {})
    ww_cfg = cfg.get("wakeword", {})
    stt_cfg = cfg.get("stt", {})
    tts_cfg = cfg.get("tts", {})
    jan_cfg = cfg.get("jan", {})
    local_cfg = cfg.get("local_llm") or {}

    models = ww_cfg.get("models")
    ww = WakeWord(
        model_name=ww_cfg.get("model", "hey_jarvis"),
        models=models if isinstance(models, list) else None,
        threshold=ww_cfg.get("threshold", 0.5),
        thresholds=ww_cfg.get("thresholds") or {},
        sample_rate=audio_cfg.get("sample_rate", 16000),
        input_device=audio_cfg.get("input_device"),
        capture_rate=audio_cfg.get("capture_rate"),
    )
    stt = build_transcriber(stt_cfg)
    narrate = tts_cfg.get("narrate") or {}
    tts = Speaker(
        voice=tts_cfg.get("voice", "en_US-amy-medium"),
        speed=tts_cfg.get("speed", 0.88),
        output_device=audio_cfg.get("output_device"),
        alsa_output=audio_cfg.get("alsa_output"),
        lead_silence_ms=tts_cfg.get("lead_silence_ms", 200),
        noise_scale=float(tts_cfg.get("noise_scale", 0.80)),
        noise_w=float(tts_cfg.get("noise_w", 0.95)),
        sentence_silence=float(tts_cfg.get("sentence_silence", 0.35)),
        narrate_url=narrate.get("url", ""),
        narrate_voice=narrate.get("voice", "am_michael"),
        narrate_speed=float(narrate.get("speed", 0.87)),
        narrate_timeout_s=float(narrate.get("timeout_s", 120)),
        narrate_pause_period_s=float(narrate.get("pause_period_s", 0.45)),
        narrate_pause_comma_s=float(narrate.get("pause_comma_s", 0.22)),
        narrate_pause_paragraph_s=float(narrate.get("pause_paragraph_s", 0.70)),
        # Package B: myra af_bella / nari af_aoede / orla af_kore
        reply_engine=str(tts_cfg.get("reply_engine", "narrate")),
        reply_voice=str(tts_cfg.get("reply_voice", "af_bella")),
        reply_speed=float(tts_cfg.get("reply_speed", 0.88)),
        reply_voices=dict(tts_cfg.get("reply_voices") or {}),
        pronounce=dict(tts_cfg.get("pronounce") or {"Orla": "Orluh", "orla": "Orluh"}),
    )
    jan = JanBrain(
        base_url=jan_cfg.get("base_url", "http://192.168.50.42:1337/v1"),
        model=jan_cfg.get("model", ""),
        api_key=jan_cfg.get("api_key", ""),
        system_prompt=jan_cfg.get("system_prompt", ""),
        timeout_s=jan_cfg.get("request_timeout_s", 180),
        host_header=jan_cfg.get("host_header", ""),
        api_mode=jan_cfg.get("api_mode", "server"),
        assistant_id=jan_cfg.get("assistant_id", ""),
        max_tokens=int(jan_cfg.get("max_tokens", 280)),
        cfg=cfg,
    )
    myra = None
    # Thin edge: gofor optional/off — room tools + Nari/Orla sessions instead.
    if local_cfg.get("enabled", False):
        myra = LocalBrain(
            base_url=local_cfg.get("base_url", "http://127.0.0.1:11434/v1"),
            model=local_cfg.get("model", "myra-gofor"),
            api_key=local_cfg.get("api_key", "ollama"),
            system_prompt=local_cfg.get("system_prompt", ""),
            timeout_s=local_cfg.get("request_timeout_s", 90),
            history_turns=local_cfg.get("history_turns", 4),
            tools_enabled=local_cfg.get("tools_enabled", True),
        )
    orla = None
    orla_cfg = cfg.get("orla") or {}
    if orla_cfg.get("enabled", True):
        orla = JanBrain(
            base_url=orla_cfg.get("base_url", "http://192.168.50.42:11434/v1"),
            model=orla_cfg.get("model", "orla"),
            api_key=orla_cfg.get("api_key", "ollama"),
            system_prompt=orla_cfg.get("system_prompt", ""),
            timeout_s=orla_cfg.get("request_timeout_s", 120),
            host_header=orla_cfg.get("host_header", ""),
            api_mode=orla_cfg.get("api_mode", "chat"),
            assistant_id=orla_cfg.get("assistant_id", ""),
            max_tokens=int(orla_cfg.get("max_tokens", 280)),
            cfg=cfg,
        )
    return ww, stt, tts, jan, myra, orla


def handle(
    intent: intents_mod.Intent,
    cfg: dict,
    jan: JanBrain,
    myra: LocalBrain | None,
    orla: JanBrain | None = None,
) -> str:
    if intent.kind == "note":
        n = cfg.get("notes", {})
        notes_mod.append_note(
            intent.text,
            local_dir=n.get("local_dir", "~/studio-notes"),
            filename=n.get("filename", "voice-notes.md"),
            sync_dir=n.get("sync_dir", ""),
        )
        return "Got it, I wrote that down."

    if intent.kind == "generate":
        # Legacy one-shot — prefer brief; still allow direct generate if already packed
        return gen_mod.generate(jan, intent.text, cfg, require_scene=True, scene_hint=intent.text)

    if intent.kind == "image_brief":
        if image_brief.is_active():
            return image_brief.feed(intent.raw or intent.text, jan, cfg)
        return image_brief.start(intent.raw or intent.text)

    if intent.kind == "recreate":
        # Never clobber an open brief with a fresh start mid-interview
        if image_brief.is_active():
            return image_brief.feed(intent.raw or intent.text, jan, cfg)
        return image_brief.start(intent.raw or intent.text, mode="recreate")

    if intent.kind == "cast_swap":
        if image_brief.is_active():
            return image_brief.feed(intent.raw or intent.text, jan, cfg)
        return image_brief.start(intent.raw or intent.text, mode="cast_swap")

    if intent.kind == "cast_batch":
        if image_brief.is_active():
            return image_brief.feed(intent.raw or intent.text, jan, cfg)
        return image_brief.start(intent.raw or intent.text, mode="cast_batch")

    if intent.kind == "brief_answer":
        return image_brief.feed(intent.raw or intent.text, jan, cfg)

    if intent.kind == "web_lookup":
        return room_tools.run_tool(
            "web_search",
            {"query": intent.text or intent.raw},
            cfg,
            jan,
        )

    if intent.kind == "pose":
        if not cfg.get("pose", {}).get("enabled", False):
            return "Pose capture is turned off in my config."
        return pose_capture.pose_to_image(intent.text, cfg)

    if intent.kind == "weather":
        return room_tools.run_tool(
            "get_weather",
            {"location": intent.text},
            cfg,
            jan,
        )

    if intent.kind == "headlines":
        return room_tools.run_tool("get_headlines", {}, cfg, jan)

    if intent.kind == "datetime":
        return room_tools.run_tool("get_datetime", {}, cfg, jan)

    if intent.kind == "screensaver_on":
        return room_tools.run_tool("enable_screensaver", {}, cfg, jan)

    if intent.kind == "screensaver_off":
        return room_tools.run_tool("disable_screensaver", {}, cfg, jan)

    if intent.kind == "comfybox_status":
        return room_tools.run_tool("show_comfybox_status", {}, cfg, jan)

    if intent.kind == "hide_display":
        return room_tools.run_tool("hide_comfybox_status", {}, cfg, jan)

    if intent.kind == "read":
        return room_tools.run_tool("read_aloud", {"query": intent.text}, cfg, jan)

    if intent.kind == "ask_jan":
        # Nari session on ComfyBox — full transcript, no Pi gofor middleman
        req = (intent.text or intent.raw).strip()
        try:
            from . import agent_pulse as _pulse

            _pulse.set_status("nari", "talking_to_myra", detail="Direct session")
            _pulse.set_status("myra", "working", detail="Relay to Nari")
        except Exception:
            pass
        reply = jan.ask(
            "You are Nari. Myra is only the room mic. "
            "Answer in 1 to 3 short spoken sentences. "
            f"Request: {req}"
        )
        try:
            from . import agent_pulse as _pulse

            _pulse.set_status("nari", "ready", detail="")
        except Exception:
            pass
        return reply

    if intent.kind == "ask_orla":
        try:
            from . import agent_pulse as _pulse

            _pulse.set_status("orla", "talking_to_myra", detail="Direct session")
            _pulse.set_status("myra", "working", detail="Relay to Orla")
        except Exception:
            pass
        reply = room_tools.run_tool(
            "ask_orla", {"request": intent.text}, cfg, jan, orla_brain=orla
        )
        try:
            from . import agent_pulse as _pulse

            _pulse.set_status("orla", "ready", detail="")
        except Exception:
            pass
        return reply

    if intent.kind == "search":
        return jan.ask(
            "Answer in 1 to 3 short spoken sentences using what you know, "
            "or say you need a web tool. "
            f"Request: {intent.raw}"
        )

    if intent.kind == "reference":
        q = (intent.text or intent.raw).strip()
        return jan.ask(
            "Help find reference direction for this subject in one short spoken sentence. "
            f"Subject: {q}"
        )

    # conversation — thin edge: Pi only relays; brains are Nari/Orla
    if intent.persona in {"nari", "jan"}:
        # Hey Nari wake → create brief or Nari chat (never Pi gofor)
        if image_brief.wants_create_brief(intent.text) or any(
            k in (intent.text or "").lower()
            for k in ("image", "picture", "generate", "draw", "recreate", "cast")
        ):
            return image_brief.start(intent.raw or intent.text)
        return jan.ask(
            "You are Nari. Answer in 1 to 3 short spoken sentences. "
            f"Request: {intent.text}"
        )

    if intent.persona == "orla":
        # Hey Orla wake → polish/display brain on Windows
        req = (intent.text or intent.raw).strip()
        return room_tools.run_tool(
            "ask_orla",
            {"request": req or "What do you need?"},
            cfg,
            jan,
            orla_brain=orla,
        )

    # Active image brief steals follow-up answers
    if image_brief.is_active():
        return image_brief.feed(intent.raw or intent.text, jan, cfg)

    # Create phrases spoken to Hey Myra → hand off to Nari brief
    if image_brief.wants_create_brief(intent.text) or any(
        k in (intent.text or "").lower()
        for k in ("make an image", "create an image", "generate", "recreate")
    ):
        return "Sending that to Nari. " + image_brief.start(intent.raw or intent.text)

    if myra is not None and myra.is_up():
        return myra.ask(intent.text, cfg, jan_brain=jan, orla_brain=orla)

    # Gofor off: polite room fallback — hand deep asks to Nari
    low = (intent.text or "").lower()
    if any(k in low for k in ("why", "how", "explain", "tell me about", "what do you think")):
        return jan.ask(intent.text)
    return (
        "I can do time, weather, notes, timers, look-ups, and the display. "
        "For images, say make an image or Hey Nari. "
        "For display polish, ask Orla."
    )


def _follow_up_cfg(cfg: dict) -> dict:
    return dict(cfg.get("follow_up") or {})


def should_open_follow_up(reply: str, intent: intents_mod.Intent, cfg: dict) -> bool:
    """Keep the mic open after a reply so 'yes' / follow-ups don't need Hey Myra."""
    fu = _follow_up_cfg(cfg)
    if not fu.get("enabled", True):
        return False
    # Keep mic open only while a brief is still active.
    if image_brief.is_active():
        return True
    # Display / notes / finished image jobs: back to wake.
    if intent.kind in {
        "screensaver_on",
        "screensaver_off",
        "comfybox_status",
        "hide_display",
        "note",
        "generate",
        "ask_orla",
        "ask_jan",
        "pose",
        "reference",
        "web_lookup",
        "image_brief",
        "brief_answer",
        "recreate",
        "cast_swap",
        "cast_batch",
    }:
        return False
    mode = str(fu.get("mode", "always")).lower()
    if mode == "always":
        return True
    if mode == "offers":
        return bool(_FOLLOW_UP_OFFER_RE.search(reply or ""))
    # questions: reply has ? or an offer phrase
    return bool(_FOLLOW_UP_OFFER_RE.search(reply or ""))


def _speak_reply(
    reply: str,
    intent: intents_mod.Intent,
    cfg: dict,
    tts: Speaker,
    myra: LocalBrain | None,
    log: logging.Logger,
) -> None:
    quality = "narrate" if intent.kind == "read" else "piper"
    chapter_stem = ""
    if intent.kind == "read":
        chapter_stem = room_tools.last_read_stem
    if myra is not None and getattr(myra, "last_tts_quality", "") == "narrate":
        quality = "narrate"
        if not chapter_stem:
            chapter_stem = room_tools.last_read_stem
        myra.last_tts_quality = "piper"
    log.info(
        "TTS quality=%s chapter_stem=%r intent=%s persona=%s",
        quality,
        chapter_stem,
        intent.kind,
        intent.persona,
    )
    tts.speak(
        reply,
        quality=quality,
        chapter_stem=chapter_stem,
        persona=intent.persona,
    )
    room_tools.last_read_stem = ""


def run_follow_up_turns(
    *,
    persona: str,
    cfg: dict,
    stt,
    tts: Speaker,
    jan: JanBrain,
    myra: LocalBrain | None,
    orla: JanBrain | None,
    seed_reply: str,
    seed_intent: intents_mod.Intent,
    log: logging.Logger,
) -> None:
    """Listen for short follow-ups without a new wake word."""
    fu = _follow_up_cfg(cfg)
    max_turns = max(0, int(fu.get("max_turns", 3)))
    # Image brief needs more slot answers without re-wake
    if image_brief.is_active():
        max_turns = max(max_turns, 6)
    if max_turns <= 0:
        return
    window_s = float(fu.get("window_s", 12))
    if image_brief.is_active():
        window_s = max(window_s, 12.0)
    silence_s = float(
        fu.get("silence_timeout_s", cfg.get("audio", {}).get("silence_timeout_s", 1.2))
    )
    max_utt = float(fu.get("max_utterance_s", 20))
    skip_ack = bool(fu.get("skip_thinking_ack", True))
    tts_ack = cfg.get("tts", {}).get("thinking_ack", True)
    tts_phrases = cfg.get("tts", {}).get("thinking_phrases") or [
        "One sec.", "Let me think.", "Searching.", "On it.",
    ]

    reply = seed_reply
    intent = seed_intent
    for turn in range(max_turns):
        if not should_open_follow_up(reply, intent, cfg) and turn > 0:
            # After first follow-up, only continue if she asked again / always mode
            if str(fu.get("mode", "always")).lower() != "always":
                break
        log.info("Follow-up listen window open (turn %d/%d, %.0fs)", turn + 1, max_turns, window_s)
        deadline = time.time() + window_s
        audio = audio_mod.record_until_silence(
            sample_rate=cfg.get("audio", {}).get("sample_rate", 16000),
            silence_timeout_s=silence_s,
            max_utterance_s=min(max_utt, max(1.0, deadline - time.time())),
            input_device=cfg.get("audio", {}).get("input_device"),
            capture_rate=cfg.get("audio", {}).get("capture_rate"),
        )
        if time.time() > deadline + 1.0:
            log.info("Follow-up window expired")
            return
        peak = audio_mod.peak_level(audio)
        text = stt.transcribe(audio, cfg.get("audio", {}).get("sample_rate", 16000))
        if not text:
            log.info("Follow-up silence (peak=%d) — back to wake word", peak)
            return
        if _FOLLOW_UP_NOISE_RE.match(text):
            log.info("Follow-up noise/blank %r — ignore, keep listening", text)
            continue
        if _HARD_ABORT_RE.search(text):
            log.warning("Hard abort from follow-up: %r", text)
            reply = image_brief.hard_abort(cfg)
            tts.speak(reply, persona=persona)
            return
        if image_brief.consume_abort():
            log.warning("Abort latch set — ending follow-up")
            return
        # Bare "no" ends follow-up only when no image brief is open
        if _FOLLOW_UP_END_RE.match(text) and not image_brief.is_active():
            log.info("Follow-up ended by user: %r", text)
            return
        if _FOLLOW_UP_WAKE_ECHO_RE.match(text):
            # Keep the mic open for the real command — don't block on gofor.
            log.info("Follow-up wake echo %r — listening again", text)
            continue

        intent = intents_mod.classify(text, persona=persona)
        # Image brief must own follow-up answers (was falling through as conversation
        # or restarting as cast_swap on "same scene…").
        if image_brief.is_active() and intent.kind in {
            "conversation", "ask_jan", "generate", "image_brief",
            "recreate", "cast_swap", "cast_batch",
        }:
            intent = intents_mod.Intent(
                "brief_answer", text, text, persona=persona
            )
        log.info(
            "Follow-up intent=%s persona=%s payload=%r",
            intent.kind,
            intent.persona,
            intent.text,
        )
        fast = intent.kind in {
            "note", "weather", "headlines", "datetime", "web_lookup",
            "screensaver_on", "screensaver_off",
            "comfybox_status", "hide_display",
            "brief_answer", "image_brief",
        }
        if tts_ack and not skip_ack and not fast and tts_phrases:
            tts.speak(random.choice(tts_phrases), persona=persona)

        reply = handle(intent, cfg, jan, myra, orla)
        if not reply:
            return
        _speak_reply(reply, intent, cfg, tts, myra, log)
        if image_brief.consume_abort() or _HARD_ABORT_RE.search(text):
            return


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("studio_edge")
    cfg = load_config()
    logging.getLogger().setLevel(cfg.get("log_level", "INFO"))

    ww, stt, tts, jan, myra, orla = build(cfg)
    ack = cfg.get("wakeword", {}).get("ack_sound", True)
    out_dev = cfg.get("audio", {}).get("output_device")
    tts_cfg = cfg.get("tts", {})
    tts_ack = tts_cfg.get("thinking_ack", True)
    tts_phrases = tts_cfg.get("thinking_phrases") or [
        "One sec.", "Let me think.", "Searching.", "On it.",
    ]
    ww_cfg = cfg.get("wakeword") or {}
    greetings = {
        "myra": ww_cfg.get("greet_myra", "Myra here."),
        "nari": ww_cfg.get("greet_nari", "Nari here."),
        "orla": ww_cfg.get("greet_orla", "Orla here."),
        # Legacy alias if an old hey_jan.onnx is still present
        "jan": ww_cfg.get("greet_nari", ww_cfg.get("greet_jan", "Nari here.")),
    }

    if not jan.is_up():
        log.warning(
            "Nari not reachable at %s yet; Hey Jan / ask_nari will fail until it's up.",
            jan.base_url,
        )
    if myra is not None and not myra.is_up():
        log.warning(
            "Optional Myra gofor not reachable at %s (thin edge works without it).",
            myra.base_url,
        )
    if orla is not None and not orla.is_up():
        log.warning(
            "Orla not reachable at %s — run D:\\studio-agent\\ollama\\orla\\start_orla.ps1.",
            orla.base_url,
        )

    running = {"go": True}
    error_state = {"last_spoken": 0.0}

    def _stop(*_a):
        running["go"] = False
        log.info("Shutting down...")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    log.info(
        "Studio Edge ready (thin edge). Hey Myra=room; Hey Nari=create; "
        "Hey Orla=display/polish; Pi=wake/STT/TTS only; gofor=%s.",
        "on" if myra is not None else "off",
    )
    try:
        from . import agent_pulse

        agent_pulse.start(cfg)
        agent_pulse.set_status("myra", "listening", detail="Wake word")
    except Exception as exc:  # noqa: BLE001
        log.warning("Agent pulse skipped: %s", exc)
    try:
        from . import display as display_mod

        display_mod.maybe_show_idle_on_start(cfg)
    except Exception as exc:  # noqa: BLE001
        log.warning("Display idle face skipped: %s", exc)
    try:
        from . import timers as timers_mod

        timers_mod.start_watcher(cfg, lambda msg: tts.speak(msg, persona="myra"))
        log.info("Timer watcher started")
    except Exception as exc:  # noqa: BLE001
        log.warning("Timer watcher skipped: %s", exc)
    tts.speak("Myra, Nari, and Orla are listening.", persona="myra")

    while running["go"]:
        try:
            try:
                from . import agent_pulse as _pulse

                _pulse.set_status("myra", "listening", detail="Wake word")
            except Exception:
                pass
            fired = ww.wait()
            persona = resolve_persona(fired, cfg)
            tts.set_persona(persona)
            log.info("Persona=%s (wake=%s)", persona, fired)
            if ack:
                audio_mod.beep(
                    output_device=out_dev,
                    alsa_output=cfg.get("audio", {}).get("alsa_output"),
                )
            # Short spoken identity so you know who answered
            greet = greetings.get(persona)
            if greet:
                try:
                    from . import agent_pulse as _pulse

                    _pulse.set_status("myra", "talking", detail="Greeting")
                except Exception:
                    pass
                tts.speak(greet, persona=persona)

            try:
                from . import agent_pulse as _pulse

                _pulse.set_status("myra", "hearing", detail="Listening for command")
            except Exception:
                pass
            audio = audio_mod.record_until_silence(
                sample_rate=cfg.get("audio", {}).get("sample_rate", 16000),
                silence_timeout_s=cfg.get("audio", {}).get("silence_timeout_s", 1.2),
                max_utterance_s=cfg.get("audio", {}).get("max_utterance_s", 30),
                input_device=cfg.get("audio", {}).get("input_device"),
                capture_rate=cfg.get("audio", {}).get("capture_rate"),
            )
            peak = audio_mod.peak_level(audio)
            text = stt.transcribe(audio, cfg.get("audio", {}).get("sample_rate", 16000))
            if not text:
                if peak < 200:
                    log.warning("Captured near-silence (peak=%d) - mic muted/unplugged?", peak)
                    tts.speak(
                        "I can't hear your microphone. Check it isn't muted.",
                        persona=persona,
                    )
                else:
                    tts.speak("Sorry, I didn't catch that.", persona=persona)
                continue

            if _HARD_ABORT_RE.search(text):
                log.warning("Hard abort from wake turn: %r", text)
                reply = image_brief.hard_abort(cfg)
                tts.speak(reply, persona=persona)
                continue

            intent = intents_mod.classify(text, persona=persona)
            # Active image brief steals soft intents so slot answers don't need Hey Nari.
            if image_brief.is_active() and intent.kind in {
                "conversation", "ask_jan", "generate", "image_brief",
                "recreate", "cast_swap", "cast_batch",
            }:
                intent = intents_mod.Intent(
                    "brief_answer", text, text, persona=persona
                )
            log.info("Intent=%s persona=%s payload=%r", intent.kind, intent.persona, intent.text)

            # Instant local shortcuts skip the thinking filler
            fast = intent.kind in {
                "note", "weather", "headlines", "datetime", "web_lookup",
                "screensaver_on", "screensaver_off",
                "comfybox_status", "hide_display",
                "image_brief", "brief_answer", "recreate", "cast_swap", "cast_batch",
            }
            # Timers/notes via tools are also local-fast when the model calls them.
            if tts_ack and not fast and tts_phrases:
                try:
                    from . import agent_pulse as _pulse

                    _pulse.set_status("myra", "thinking", detail=intent.kind)
                except Exception:
                    pass
                tts.speak(random.choice(tts_phrases), persona=persona)

            try:
                from . import agent_pulse as _pulse

                if intent.kind in {
                    "ask_jan", "generate", "image_brief", "brief_answer",
                    "recreate", "cast_swap", "cast_batch",
                }:
                    _pulse.set_status("nari", "talking_to_myra", detail="Create session")
                    _pulse.set_status("myra", "working", detail="Route to Nari")
                elif intent.kind == "ask_orla":
                    _pulse.set_status("orla", "talking_to_myra", detail="Request from Myra")
                    _pulse.set_status("myra", "working", detail="Ask Orla")
                else:
                    _pulse.set_status("myra", "working", detail=intent.kind)
            except Exception:
                pass

            reply = handle(intent, cfg, jan, myra, orla)
            if reply:
                try:
                    from . import agent_pulse as _pulse

                    _pulse.set_status("myra", "talking", detail="Reply")
                except Exception:
                    pass
                _speak_reply(reply, intent, cfg, tts, myra, log)
                try:
                    from . import agent_pulse as _pulse

                    _pulse.set_status("nari", "ready", detail="")
                    _pulse.set_status("orla", "ready", detail="")
                except Exception:
                    pass
                if should_open_follow_up(reply, intent, cfg):
                    run_follow_up_turns(
                        persona=persona,
                        cfg=cfg,
                        stt=stt,
                        tts=tts,
                        jan=jan,
                        myra=myra,
                        orla=orla,
                        seed_reply=reply,
                        seed_intent=intent,
                        log=log,
                    )
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            log.exception("Loop error: %s", exc)
            try:
                from . import agent_pulse as _pulse

                _pulse.set_status("myra", "error", detail=type(exc).__name__, ok=False)
            except Exception:
                pass
            # Mic busy / wrong device: don't spam TTS — two processes often cause this.
            try:
                import sounddevice as sd  # noqa: WPS433

                portaudio_err = isinstance(exc, sd.PortAudioError)
            except Exception:  # noqa: BLE001
                portaudio_err = "PortAudioError" in type(exc).__name__
            if portaudio_err:
                time.sleep(5)
                continue
            try:
                now = time.time()
                if now - error_state["last_spoken"] > 60:
                    tts.speak(
                        "Something went wrong, but I'm still here.",
                        persona="myra",
                    )
                    error_state["last_spoken"] = now
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
