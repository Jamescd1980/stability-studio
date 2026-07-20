"""Text-to-speech: Piper for short replies; Kokoro narrate for book read-aloud."""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from . import audio as audio_mod

log = logging.getLogger("studio_edge.tts")

# Symbols worth speaking as words rather than dropping (keeps meaning of "50%", "A&B").
_SPOKEN_SYMBOLS = {
    "%": " percent",
    "&": " and ",
    "+": " plus ",
    "=": " equals ",
    "@": " at ",
    "\u00b0": " degrees",
    "_": " ",  # snake_case identifiers -> spaced words (generate_image -> generate image)
}
# After symbol substitution, keep letters/digits/whitespace + speech punctuation only.
# Everything else (markdown *_#`~>, brackets clutter, emoji, box-drawing) is dropped.
_SPEECH_KEEP = re.compile(r"[^0-9A-Za-z\u00c0-\u024f\s.,!?;:'\"()\-]")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:[^)]+)\)")          # [text](url) -> text
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)             # drop fenced code blocks
_INLINE_CODE = re.compile(r"`([^`]*)`")                      # `code` -> code
_MD_EMPHASIS = re.compile(r"(\*{1,3}|~{2})")                 # ** and ~~ markers (_ -> space below)
_MULTISPACE = re.compile(r"[ \t]{2,}")
_MULTINEWLINE = re.compile(r"\n{2,}")

# Curly / typographic apostrophes → ASCII so contractions survive cleaning.
_APOSTROPHE_CHARS = str.maketrans({
    "\u2019": "'",  # ’
    "\u2018": "'",  # ‘
    "\u02BC": "'",  # ʼ
    "\u2032": "'",  # ′
    "`": "'",
})

# Expand before TTS — Kokoro/Piper often mangle "wasn't" → "wosenty" if the
# apostrophe is lost or the model guesses wrong.
_CONTRACTIONS: list[tuple[re.Pattern[str], str]] = [
    # Apostrophe forms
    (re.compile(r"\bwasn't\b", re.I), "was not"),
    (re.compile(r"\bweren't\b", re.I), "were not"),
    (re.compile(r"\bisn't\b", re.I), "is not"),
    (re.compile(r"\baren't\b", re.I), "are not"),
    (re.compile(r"\bain't\b", re.I), "is not"),
    (re.compile(r"\bhasn't\b", re.I), "has not"),
    (re.compile(r"\bhaven't\b", re.I), "have not"),
    (re.compile(r"\bhadn't\b", re.I), "had not"),
    (re.compile(r"\bdoesn't\b", re.I), "does not"),
    (re.compile(r"\bdon't\b", re.I), "do not"),
    (re.compile(r"\bdidn't\b", re.I), "did not"),
    (re.compile(r"\bcan't\b", re.I), "cannot"),
    (re.compile(r"\bcouldn't\b", re.I), "could not"),
    (re.compile(r"\bwouldn't\b", re.I), "would not"),
    (re.compile(r"\bshouldn't\b", re.I), "should not"),
    (re.compile(r"\bwon't\b", re.I), "will not"),
    (re.compile(r"\bmustn't\b", re.I), "must not"),
    (re.compile(r"\bneedn't\b", re.I), "need not"),
    (re.compile(r"\bmightn't\b", re.I), "might not"),
    (re.compile(r"\bshan't\b", re.I), "shall not"),
    # Apostrophe already stripped (wasnt → wosenty in Kokoro)
    (re.compile(r"\bwasnt\b", re.I), "was not"),
    (re.compile(r"\bwerent\b", re.I), "were not"),
    (re.compile(r"\bisnt\b", re.I), "is not"),
    (re.compile(r"\barent\b", re.I), "are not"),
    (re.compile(r"\bhasnt\b", re.I), "has not"),
    (re.compile(r"\bhavent\b", re.I), "have not"),
    (re.compile(r"\bhadnt\b", re.I), "had not"),
    (re.compile(r"\bdoesnt\b", re.I), "does not"),
    (re.compile(r"\bdont\b", re.I), "do not"),
    (re.compile(r"\bdidnt\b", re.I), "did not"),
    (re.compile(r"\bcant\b", re.I), "cannot"),
    (re.compile(r"\bcouldnt\b", re.I), "could not"),
    (re.compile(r"\bwouldnt\b", re.I), "would not"),
    (re.compile(r"\bshouldnt\b", re.I), "should not"),
    (re.compile(r"\bwont\b", re.I), "will not"),
    (re.compile(r"\bit's\b", re.I), "it is"),
    (re.compile(r"\bthat's\b", re.I), "that is"),
    (re.compile(r"\bwhat's\b", re.I), "what is"),
    (re.compile(r"\bwho's\b", re.I), "who is"),
    (re.compile(r"\bthere's\b", re.I), "there is"),
    (re.compile(r"\bhere's\b", re.I), "here is"),
    (re.compile(r"\bhe's\b", re.I), "he is"),
    (re.compile(r"\bshe's\b", re.I), "she is"),
    (re.compile(r"\bwe're\b", re.I), "we are"),
    (re.compile(r"\bthey're\b", re.I), "they are"),
    (re.compile(r"\byou're\b", re.I), "you are"),
    (re.compile(r"\bI'm\b"), "I am"),
    (re.compile(r"\bi'm\b"), "I am"),
    (re.compile(r"\bI've\b"), "I have"),
    (re.compile(r"\bi've\b"), "I have"),
    (re.compile(r"\bwe've\b", re.I), "we have"),
    (re.compile(r"\bthey've\b", re.I), "they have"),
    (re.compile(r"\byou've\b", re.I), "you have"),
    (re.compile(r"\bI'll\b"), "I will"),
    (re.compile(r"\bi'll\b"), "I will"),
    (re.compile(r"\bwe'll\b", re.I), "we will"),
    (re.compile(r"\bthey'll\b", re.I), "they will"),
    (re.compile(r"\byou'll\b", re.I), "you will"),
    (re.compile(r"\bhe'll\b", re.I), "he will"),
    (re.compile(r"\bshe'll\b", re.I), "she will"),
    (re.compile(r"\bit'll\b", re.I), "it will"),
    (re.compile(r"\bI'd\b"), "I would"),
    (re.compile(r"\bi'd\b"), "I would"),
    (re.compile(r"\bwe'd\b", re.I), "we would"),
    (re.compile(r"\bthey'd\b", re.I), "they would"),
    (re.compile(r"\byou'd\b", re.I), "you would"),
    (re.compile(r"\blet's\b", re.I), "let us"),
    (re.compile(r"\byesterday's\b", re.I), "yesterdays"),
]


def expand_contractions(text: str) -> str:
    """Normalize apostrophes and expand common contractions for clearer TTS.

    Kokoro often turns "wasn't" into "wosenty" when the apostrophe is curly
    (stripped to "wasnt") or when it mis-reads the contraction.
    """
    if not text:
        return ""
    s = text.translate(_APOSTROPHE_CHARS)
    for pat, repl in _CONTRACTIONS:
        def _sub(m: re.Match[str], r: str = repl) -> str:
            src = m.group(0)
            if src.isupper():
                return r.upper()
            if src[:1].isupper():
                parts = r.split()
                parts[0] = parts[0][:1].upper() + parts[0][1:]
                return " ".join(parts)
            return r
        s = pat.sub(_sub, s)
    return s


# Homophone: read (reed / present) vs read (red / past). Piper & Kokoro often guess wrong.
# Strategy: lock clear past contexts to "red", then force remaining "read" → "reed"
# (voice-assistant / book cues are almost always the present/imperative).
_READ_WORD = re.compile(r"\bread\b", re.I)


def _match_case(src: str, replacement: str) -> str:
    """Roughly preserve capitalization of the matched word(s)."""
    if src.isupper():
        return replacement.upper()
    if src[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def fix_homophones_for_speech(text: str, *, default_read: str = "reed") -> str:
    """Disambiguate common TTS homophones (esp. read/reed vs read/red).

    Book narration (default_read='red'): prefer past-tense 'red'; do NOT apply
    assistant command rules like 'read the' → 'reed' (those break prose such as
    'and read the first line aloud').
    """
    if not text:
        return ""
    s = text

    def _sub_past_aux(m: re.Match[str]) -> str:
        aux, word = m.group(1), m.group(2)
        return f"{aux} {_match_case(word, 'red')}"

    def _sub_past_adv(m: re.Match[str]) -> str:
        adv, word = m.group(1), m.group(2)
        return f"{adv} {_match_case(word, 'red')}"

    def _sub_reed(m: re.Match[str]) -> str:
        return m.group(0).replace(m.group("w"), _match_case(m.group("w"), "reed"))

    # Clear past → red (always)
    s = re.sub(r"\b(have|has|had|having)\s+(read)\b", _sub_past_aux, s, flags=re.I)
    s = re.sub(r"\b(was|were|been|being)\s+(read)\b", _sub_past_aux, s, flags=re.I)
    s = re.sub(r"\b(already|never|just)\s+(read)\b", _sub_past_adv, s, flags=re.I)
    s = re.sub(
        r"\b(re-read|reread)\b",
        lambda m: _match_case(m.group(0), "re-red"),
        s,
        flags=re.I,
    )
    # "and read …" / "then read …" in narrative → past red
    s = re.sub(r"\b(and|then|she|he|i|we|they)\s+(read)\b", _sub_past_aux, s, flags=re.I)

    if default_read == "red":
        # Book mode: everything left is past/default red — never force reed.
        s = _READ_WORD.sub(lambda m: _match_case(m.group(0), "red"), s)
        return s

    # Assistant mode: present / imperative → reed
    s = re.sub(r"\b(please|kindly)\s+(?P<w>read)\b", _sub_reed, s, flags=re.I)
    s = re.sub(
        r"\b(will|would|can|could|should|must|may|might|shall)\s+(?P<w>read)\b",
        _sub_reed,
        s,
        flags=re.I,
    )
    s = re.sub(r"\bto\s+(?P<w>read)\b", _sub_reed, s, flags=re.I)
    s = re.sub(r"\b(let'?s|gonna)\s+(?P<w>read)\b", _sub_reed, s, flags=re.I)
    s = re.sub(
        r"\b(?P<w>read)\s+(?P<rest>chapter|me|the|this|that|aloud|out)\b",
        lambda m: f"{_match_case(m.group('w'), 'reed')} {m.group('rest')}",
        s,
        flags=re.I,
    )
    s = _READ_WORD.sub(lambda m: _match_case(m.group(0), default_read), s)
    return s


def _smooth_for_narration(text: str) -> str:
    """Break hard-to-speak punctuation for book TTS (em dashes, dense asides)."""
    s = text
    # Em/en dash asides → full stop (clearer than a run-on)
    s = re.sub(r"\s*[\u2014\u2013—–]+\s*", ". ", s)
    s = re.sub(r"\s+-\s+", ". ", s)
    s = re.sub(r"\bmid-turn\b", "mid turn", s, flags=re.I)
    # Capitalize first letter after a sentence break we just inserted
    s = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), s)
    s = re.sub(r"\s{2,}", " ", s)
    return s


def apply_pronunciations(text: str, mapping: dict[str, str] | None) -> str:
    """Replace book-name spellings with TTS-friendly forms (e.g. Orla → Or luck)."""
    if not text or not mapping:
        return text or ""
    s = text
    # Longer keys first so multi-word forms win
    for src, spoken in sorted(mapping.items(), key=lambda kv: len(str(kv[0])), reverse=True):
        if not src or not spoken:
            continue
        s = re.sub(rf"\b{re.escape(str(src))}\b", str(spoken), s, flags=re.I)
    return s


def clean_for_speech(
    text: str,
    *,
    default_read: str = "reed",
    pronounce: dict[str, str] | None = None,
) -> str:
    """Strip markdown, emoji and stray symbols so TTS doesn't read them aloud.

    Jan's replies often contain markdown (**bold**, headings, bullet points) and
    emoji; spoken verbatim these become "asterisk asterisk" / symbol noise. We drop
    the decorations, voice a few meaningful symbols as words, and keep normal
    sentence punctuation so prosody survives.
    """
    if not text:
        return ""
    s = apply_pronunciations(text, pronounce)
    s = _CODE_FENCE.sub(" ", s)
    s = _INLINE_CODE.sub(r"\1", s)
    s = _MD_LINK.sub(r"\1", s)
    s = _MD_EMPHASIS.sub("", s)
    # Strip leading markdown structure per line (headings, bullets, quotes, numbering).
    lines = []
    for line in s.splitlines():
        line = re.sub(r"^\s*#{1,6}\s*", "", line)        # # heading
        line = re.sub(r"^\s*[-*+]\s+", "", line)          # - bullet
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)        # 1. numbered
        line = re.sub(r"^\s*>\s?", "", line)              # > quote
        lines.append(line)
    s = "\n".join(lines)
    for sym, word in _SPOKEN_SYMBOLS.items():
        s = s.replace(sym, word)
    # Expand contractions BEFORE stripping punctuation — curly apostrophes would
    # otherwise turn "wasn't" into "wasnt" → "wosenty".
    s = expand_contractions(s)
    if default_read == "red":
        s = _smooth_for_narration(s)
    s = _SPEECH_KEEP.sub(" ", s)
    # Second pass: apostrophe-stripped contractions (wasnt)
    s = expand_contractions(s)
    s = _MULTISPACE.sub(" ", s)
    s = _MULTINEWLINE.sub("\n", s)
    s = fix_homophones_for_speech(s.strip(), default_read=default_read)
    return s.strip()


def _find_piper() -> str | None:
    """Locate the piper executable.

    When run from a venv (or via `venv/bin/python -m ...` under systemd) piper lives
    next to the running interpreter but isn't on the system PATH, so check there first.
    """
    candidate = Path(sys.executable).parent / "piper"
    if candidate.exists():
        return str(candidate)
    return shutil.which("piper")


class Speaker:
    def __init__(
        self,
        voice: str = "en_US-amy-medium",
        voices_dir: str | None = None,
        speed: float = 1.0,
        output_device: int | None = None,
        alsa_output: str | None = None,
        lead_silence_ms: int = 200,
        *,
        noise_scale: float = 0.80,
        noise_w: float = 0.95,
        sentence_silence: float = 0.35,
        narrate_url: str = "",
        narrate_voice: str = "am_michael",
        narrate_speed: float = 0.87,
        narrate_timeout_s: float = 120.0,
        narrate_pause_period_s: float = 0.45,
        narrate_pause_comma_s: float = 0.22,
        narrate_pause_paragraph_s: float = 0.70,
        # Short replies: "narrate" = Kokoro (warmer), "piper" = on-device.
        reply_engine: str = "narrate",
        reply_voice: str = "af_heart",
        reply_speed: float = 0.88,
        reply_voices: dict[str, str] | None = None,
        pronounce: dict[str, str] | None = None,
    ) -> None:
        self.speed = speed
        self.noise_scale = noise_scale
        self.noise_w = noise_w
        self.sentence_silence = sentence_silence
        self.output_device = output_device
        self.alsa_output = alsa_output
        self.lead_silence_ms = lead_silence_ms
        self.narrate_url = (narrate_url or "").rstrip("/")
        self.narrate_voice = narrate_voice
        self.narrate_speed = narrate_speed
        self.narrate_timeout_s = narrate_timeout_s
        self.narrate_pause_period_s = narrate_pause_period_s
        self.narrate_pause_comma_s = narrate_pause_comma_s
        self.narrate_pause_paragraph_s = narrate_pause_paragraph_s
        self.reply_engine = (reply_engine or "piper").strip().lower()
        self.reply_voice = reply_voice or "af_heart"
        self.reply_speed = float(reply_speed)
        self.reply_voices = {
            str(k).lower(): str(v)
            for k, v in (reply_voices or {}).items()
            if k and v
        }
        self.pronounce = dict(pronounce or {})
        self._active_persona = "myra"
        self.piper = _find_piper()
        if not self.piper:
            log.warning("piper executable not found (pip install piper-tts in the venv)")
        vdir = Path(voices_dir or os.path.expanduser("~/piper-voices"))
        self.model_path = vdir / f"{voice}.onnx"
        if not self.model_path.exists():
            log.warning("Piper voice not found at %s (run 03-download-models.sh)", self.model_path)

    def set_persona(self, persona: str | None) -> None:
        """Remember who is speaking for subsequent speak() calls."""
        p = (persona or "myra").strip().lower() or "myra"
        if p == "jan":
            p = "nari"
        self._active_persona = p

    def voice_for(self, persona: str | None = None) -> str:
        """Kokoro reply voice for persona (package map → reply_voice fallback)."""
        p = (persona or self._active_persona or "myra").strip().lower() or "myra"
        if p == "jan":
            p = "nari"
        return self.reply_voices.get(p) or self.reply_voice

    def speak(
        self,
        text: str,
        *,
        quality: str = "piper",
        chapter_stem: str = "",
        persona: str | None = None,
    ) -> None:
        """Speak text. quality=piper (default) or narrate (Kokoro on studio box)."""
        if persona is not None:
            self.set_persona(persona)
        # Book prose defaults leftover "read" → red; short assistant cues → reed.
        default_read = "red" if quality == "narrate" else "reed"
        text = clean_for_speech(
            text or "",
            default_read=default_read,
            pronounce=self.pronounce,
        )
        if not text:
            return
        if quality == "narrate" and self.narrate_url:
            stem = (chapter_stem or "").strip()
            if stem and self._speak_prerendered(stem):
                return
            if self._speak_narrate(
                text,
                voice=self.narrate_voice,
                speed=self.narrate_speed,
            ):
                return
            # Do not dump a whole chapter into Piper — it has no longform chunking.
            if len(text) > 400:
                log.error("Narrate TTS failed; refusing long Piper fallback (%d chars)", len(text))
                self._speak_piper(
                    "I found the chapter, but the book narrator on the studio box is down."
                )
                return
            log.warning("Narrate TTS failed; falling back to Piper for short text")
        elif (
            quality == "piper"
            and self.reply_engine == "narrate"
            and self.narrate_url
        ):
            use_voice = self.voice_for(persona)
            log.info("Kokoro reply persona=%s voice=%s", self._active_persona, use_voice)
            if self._speak_narrate(
                text,
                voice=use_voice,
                speed=self.reply_speed,
                # Short replies: lighter punctuation pauses than book narration.
                pause_period_s=min(self.narrate_pause_period_s, 0.32),
                pause_comma_s=min(self.narrate_pause_comma_s, 0.16),
                pause_paragraph_s=min(self.narrate_pause_paragraph_s, 0.40),
            ):
                return
            log.warning("Kokoro reply voice failed; falling back to Piper")
        self._speak_piper(text)

    def _speak_piper(self, text: str) -> None:
        if not self.piper:
            log.error("cannot speak: piper executable not found")
            return
        out = audio_mod.temp_wav_path()
        # piper CLI: text on stdin -> wav file. length_scale ~ 1/speed.
        length_scale = f"{1.0 / max(self.speed, 0.1):.3f}"
        cmd = [
            self.piper,
            "--model", str(self.model_path),
            "--output_file", out,
            "--length_scale", length_scale,
            "--noise-scale", f"{self.noise_scale:.3f}",
            "--noise-w-scale", f"{self.noise_w:.3f}",
            "--sentence-silence", f"{self.sentence_silence:.3f}",
        ]
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio_mod.prepend_silence(out, self.lead_silence_ms)
            audio_mod.play_wav(out, output_device=self.output_device,
                               alsa_output=self.alsa_output)
        except FileNotFoundError:
            log.error("piper CLI not found. pip install piper-tts")
        except subprocess.CalledProcessError as exc:
            log.error("piper failed: %s", exc)
        finally:
            try:
                os.remove(out)
            except OSError:
                pass

    def _speak_prerendered(self, stem: str) -> bool:
        """Play offline-rendered chapter WAV from comfybox if it exists."""
        out = audio_mod.temp_wav_path()
        try:
            r = requests.get(
                f"{self.narrate_url}/v1/rendered/{stem}.wav",
                timeout=60,
            )
            if r.status_code == 404:
                return False
            r.raise_for_status()
            Path(out).write_bytes(r.content)
            audio_mod.prepend_silence(out, self.lead_silence_ms)
            audio_mod.play_wav(out, output_device=self.output_device,
                               alsa_output=self.alsa_output)
            log.info("Played pre-rendered chapter %s from studio box", stem)
            return True
        except requests.RequestException as exc:
            log.debug("No pre-rendered chapter %s (%s)", stem, exc)
            return False
        finally:
            try:
                os.remove(out)
            except OSError:
                pass

    def _speak_narrate(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float | None = None,
        pause_period_s: float | None = None,
        pause_comma_s: float | None = None,
        pause_paragraph_s: float | None = None,
    ) -> bool:
        """POST text to Kokoro narrate service; play returned WAV on the Pi."""
        out = audio_mod.temp_wav_path()
        use_voice = voice or self.narrate_voice
        use_speed = self.narrate_speed if speed is None else speed
        try:
            r = requests.post(
                f"{self.narrate_url}/v1/tts",
                json={
                    "text": text,
                    "voice": use_voice,
                    "speed": use_speed,
                    "pause_period_s": (
                        self.narrate_pause_period_s
                        if pause_period_s is None
                        else pause_period_s
                    ),
                    "pause_comma_s": (
                        self.narrate_pause_comma_s
                        if pause_comma_s is None
                        else pause_comma_s
                    ),
                    "pause_paragraph_s": (
                        self.narrate_pause_paragraph_s
                        if pause_paragraph_s is None
                        else pause_paragraph_s
                    ),
                },
                # Short replies shouldn't wait the full book timeout.
                timeout=min(self.narrate_timeout_s, 45.0) if len(text) < 500 else self.narrate_timeout_s,
            )
            r.raise_for_status()
            Path(out).write_bytes(r.content)
            audio_mod.prepend_silence(out, self.lead_silence_ms)
            audio_mod.play_wav(out, output_device=self.output_device,
                               alsa_output=self.alsa_output)
            log.info("Kokoro TTS voice=%s chars=%d", use_voice, len(text))
            return True
        except requests.RequestException as exc:
            log.error("Narrate TTS request failed (voice=%s): %s", use_voice, exc)
            return False
        finally:
            try:
                os.remove(out)
            except OSError:
                pass

    def narrate_is_up(self) -> bool:
        if not self.narrate_url:
            return False
        try:
            r = requests.get(f"{self.narrate_url}/health", timeout=3)
            return r.ok
        except requests.RequestException:
            return False
