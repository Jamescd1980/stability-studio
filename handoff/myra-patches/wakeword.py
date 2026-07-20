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
    """Blocks until a configured wake word is heard."""

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        models: list[str] | None = None,
        threshold: float = 0.5,
        thresholds: dict[str, float] | None = None,
        sample_rate: int = 16000,
        input_device: int | None = None,
        capture_rate: int | None = None,
    ) -> None:
        if _OWWModel is None:
            raise RuntimeError("openwakeword not installed")
        self.threshold = threshold
        self.thresholds = {k.lower(): float(v) for k, v in (thresholds or {}).items()}
        self.sample_rate = sample_rate
        self.capture_rate = capture_rate or sample_rate
        self.input_device = input_device
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
                # Mixed custom + built-in: load customs; if only customs, that's fine.
                # openWakeWord accepts a list of paths; built-ins by name in a second load
                # is awkward — if both present, load paths first and warn about named.
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
                # All built-in names — openWakeWord loads each by id when passed as list.
                self.model = _OWWModel(wakeword_models=named_models)
        except Exception as exc:
            log.warning("Wake models %s unavailable (%s); loading defaults.", self.model_specs, exc)
            self.model = _OWWModel()

        log.info("Wake listening for: %s", self.model_specs)

    def _threshold_for(self, name: str) -> float:
        low = name.lower()
        for k, v in self.thresholds.items():
            if k == low or k in low or low in k:
                return v
        return self.threshold

    def wait(self) -> str:
        """Block until wake word detected; return the model key that fired."""
        if sd is None:
            raise RuntimeError("sounddevice not available")
        self.model.reset()
        with sd.InputStream(
            samplerate=self.capture_rate,
            channels=1,
            dtype="int16",
            blocksize=self.capture_chunk,
            device=self.input_device,
        ) as stream:
            while True:
                block, _ = stream.read(self.capture_chunk)
                audio = block.reshape(-1)
                if self.capture_rate != self.sample_rate:
                    audio = resample_int16(audio, self.capture_rate, self.sample_rate)
                scores = self.model.predict(audio)
                for name, score in scores.items():
                    thr = self._threshold_for(name)
                    if score >= thr:
                        log.info("Wake word '%s' (%.2f >= %.2f)", name, score, thr)
                        return name
