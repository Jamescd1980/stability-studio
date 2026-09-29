"""Wake-word detection via openWakeWord (single or multi-model)."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .audio import resample_int16

log = logging.getLogger("studio_edge.wakeword")

try:
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None

try:
    from openwakeword.model import Model as _OWWModel
except Exception as exc:  # pragma: no cover
    _OWWModel = None
    log.warning("openwakeword unavailable: %s", exc)


def _is_model_path(name: str) -> bool:
    return os.path.sep in name or name.lower().endswith((".onnx", ".tflite"))


def _expand_model(name: str) -> str:
    return os.path.expanduser(name)


def resolve_persona(fired_key: str, cfg: dict) -> str:
    """Map an openWakeWord score key to persona myra | nari | orla."""
    ww = cfg.get("wakeword") or {}
    mapping = ww.get("persona_map") or {}
    key = (fired_key or "").lower()
    # Hardware mute button released → treat as Myra wake
    if key.startswith("unmute") or key == "mic_unmute":
        return str(ww.get("default_persona", "myra")).lower()
    # Exact / substring match against configured map keys
    for map_key, persona in mapping.items():
        mk = str(map_key).lower()
        if mk == key or mk in key or key in mk:
            return str(persona).lower()
    # Heuristic fallbacks (jan kept as legacy alias → nari)
    if "orla" in key or "orluh" in key:
        return "orla"
    if "nari" in key or "jan" in key:
        return "nari"
    if "myra" in key or "mira" in key or "jarvis" in key:
        return "myra"
    return str(ww.get("default_persona", "myra")).lower()


class WakeWord:
    """Blocks until a configured wake word is heard (or mic unmute, if enabled)."""

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        models: list[str] | None = None,
        threshold: float = 0.5,
        thresholds: dict[str, float] | None = None,
        sample_rate: int = 16000,
        input_device: int | None = None,
        capture_rate: int | None = None,
        unmute_as_wake: bool = True,
        mute_peak: int = 40,
        unmute_peak: int = 180,
        mute_hold_chunks: int = 12,
        unmute_confirm_chunks: int = 3,
    ) -> None:
        if _OWWModel is None:
            raise RuntimeError("openwakeword not installed")
        self.threshold = threshold
        self.thresholds = {k.lower(): float(v) for k, v in (thresholds or {}).items()}
        self.sample_rate = sample_rate
        self.capture_rate = capture_rate or sample_rate
        self._input_device_cfg = input_device
        from .audio import resolve_input_device

        # Wait for USB SoloCast after reboot (PortAudio list lags ALSA).
        self.input_device = resolve_input_device(self._input_device_cfg, wait_s=60.0)
        if self.input_device is None:
            log.warning(
                "No input device matching %r yet — will retry each wake wait",
                self._input_device_cfg,
            )
        self.unmute_as_wake = bool(unmute_as_wake)
        self.mute_peak = int(mute_peak)
        self.unmute_peak = int(unmute_peak)
        self.mute_hold_chunks = max(1, int(mute_hold_chunks))
        self.unmute_confirm_chunks = max(1, int(unmute_confirm_chunks))
        # Prefer explicit multi-model list; else single model_name for back-compat.
        raw_list = [m for m in (models or []) if m] or [model_name]
        expanded = [_expand_model(m) for m in raw_list]
        # Skip missing ONNX paths so Myra can boot while new wakes train.
        kept: list[str] = []
        for m in expanded:
            if _is_model_path(m) and not Path(m).is_file():
                log.warning("Wake model missing (skip until trained): %s", m)
                continue
            kept.append(m)
        if not kept:
            raise RuntimeError(
                "No wake models found. Need hey_myra.onnx (and hey_nari / hey_orla when trained)."
            )
        self.model_specs = kept
        self.model_name = self.model_specs[0]

        self.chunk = 1280
        self.capture_chunk = int(self.chunk * self.capture_rate / self.sample_rate)

        path_models = [m for m in self.model_specs if _is_model_path(m)]
        named_models = [m for m in self.model_specs if not _is_model_path(m)]

        try:
            if path_models:
                missing = [m for m in path_models if not Path(m).exists()]
                if missing:
                    raise FileNotFoundError(f"wake model(s) missing: {missing}")
                framework = "onnx"
                if all(m.lower().endswith(".tflite") for m in path_models):
                    framework = "tflite"
                self.model = _OWWModel(wakeword_models=path_models, inference_framework=framework)
                if named_models:
                    log.warning(
                        "Built-in wake names %s ignored while custom .onnx/.tflite models are set.",
                        named_models,
                    )
            else:
                self.model = _OWWModel(wakeword_models=named_models)
        except Exception as exc:
            log.warning("Wake models %s unavailable (%s); loading defaults.", self.model_specs, exc)
            self.model = _OWWModel()

        log.info("Wake listening for: %s", self.model_specs)
        log.info(
            "Wake capture device=%r rate=%s→%s threshold=%.2f unmute_as_wake=%s "
            "(mute_peak=%d unmute_peak=%d)",
            self.input_device,
            self.capture_rate,
            self.sample_rate,
            self.threshold,
            self.unmute_as_wake,
            self.mute_peak,
            self.unmute_peak,
        )

    def _threshold_for(self, name: str) -> float:
        low = name.lower()
        for k, v in self.thresholds.items():
            if k == low or k in low or low in k:
                return v
        return self.threshold

    def wait(self) -> str:
        """Block until wake word or mic-unmute edge; return the model key that fired."""
        if sd is None:
            raise RuntimeError("sounddevice not available")
        from .audio import frames_to_mono, input_channel_count, resolve_input_device

        # Re-resolve in case USB appeared after boot or card index shifted.
        resolved = resolve_input_device(self._input_device_cfg, wait_s=30.0)
        if resolved is None:
            raise RuntimeError(
                f"No input device matching {self._input_device_cfg!r} (is SoloCast plugged in?)"
            )
        self.input_device = resolved
        self.model.reset()

        ch = input_channel_count(self.input_device)
        muted_streak = 0
        unmuted_streak = 0
        was_muted = False
        idle_chunks = 0
        with sd.InputStream(
            samplerate=self.capture_rate,
            channels=ch,
            dtype="int16",
            blocksize=self.capture_chunk,
            device=self.input_device,
        ) as stream:
            while True:
                block, _ = stream.read(self.capture_chunk)
                audio = frames_to_mono(block)
                # Peak on capture-rate samples (mute zeros the SoloCast stream).
                peak = int(max(abs(int(x)) for x in audio)) if len(audio) else 0

                if self.unmute_as_wake:
                    if peak <= self.mute_peak:
                        muted_streak += 1
                        unmuted_streak = 0
                        if muted_streak >= self.mute_hold_chunks:
                            if not was_muted:
                                log.info(
                                    "Mic looks muted (peak<=%d for %d chunks) — "
                                    "unmute will wake Myra",
                                    self.mute_peak,
                                    muted_streak,
                                )
                            was_muted = True
                    elif was_muted:
                        # Stay armed through soft/partial levels; only clear after a real wake.
                        # Ignore single full-scale unmute pops (USB button spike ~32767).
                        if peak >= 30000:
                            unmuted_streak = 0
                            continue
                        if peak >= self.unmute_peak:
                            unmuted_streak += 1
                            if unmuted_streak >= self.unmute_confirm_chunks:
                                log.info(
                                    "Mic unmute wake (peak=%d >= %d after mute)",
                                    peak,
                                    self.unmute_peak,
                                )
                                return "unmute_myra"
                        else:
                            unmuted_streak = 0
                    else:
                        muted_streak = 0
                        unmuted_streak = 0

                idle_chunks += 1
                if idle_chunks % 750 == 0:  # ~60s at 80ms/chunk
                    log.info(
                        "Wake idle (peak=%d was_muted=%s) — still listening",
                        peak,
                        was_muted,
                    )

                if self.capture_rate != self.sample_rate:
                    audio = resample_int16(audio, self.capture_rate, self.sample_rate)
                scores = self.model.predict(audio)
                for name, score in scores.items():
                    thr = self._threshold_for(name)
                    if score >= thr:
                        log.info("Wake word '%s' (%.2f >= %.2f)", name, score, thr)
                        return name
