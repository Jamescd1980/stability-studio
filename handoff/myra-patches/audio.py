"""Microphone capture (with simple VAD) and audio playback."""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
import wave
from collections import deque

import numpy as np

log = logging.getLogger("studio_edge.audio")

try:
    import sounddevice as sd
except Exception as exc:  # pragma: no cover - hardware dep
    sd = None
    log.warning("sounddevice unavailable: %s", exc)

try:
    import webrtcvad
except Exception:  # pragma: no cover
    webrtcvad = None

# WebRTC VAD only accepts these capture rates.
_VAD_RATES = (8000, 16000, 32000, 48000)


def resolve_input_device(device, *, wait_s: float = 0.0):
    """Resolve config name/index to a PortAudio device id.

    SoloCast often enumerates as ``HyperX SoloCast 2: USB Audio (hw:2,0)`` —
    substring match against input-capable devices only.
    After reboot, USB can lag — pass wait_s to retry until it appears.
    """
    if sd is None or device is None:
        return device
    if isinstance(device, int):
        return device
    query = str(device).strip()
    if not query:
        return device

    deadline = time.time() + max(0.0, float(wait_s))
    last_err = None
    while True:
        try:
            # PortAudio caches device list — force refresh when waiting.
            try:
                sd._terminate()  # type: ignore[attr-defined]
                sd._initialize()  # type: ignore[attr-defined]
            except Exception:
                pass
            matches = []
            for i, info in enumerate(sd.query_devices()):
                if int(info.get("max_input_channels") or 0) <= 0:
                    continue
                name = str(info.get("name") or "")
                if query == name or query.lower() in name.lower():
                    matches.append((i, name))
            if len(matches) == 1:
                log.info("Audio input resolved %r → %s (%r)", query, matches[0][0], matches[0][1])
                return matches[0][0]
            if len(matches) > 1:
                for i, name in matches:
                    if "USB Audio" in name or name.lower().startswith(query.lower()):
                        log.info("Audio input resolved %r → %s (%r)", query, i, name)
                        return i
                log.info("Audio input resolved %r → %s (%r)", query, matches[0][0], matches[0][1])
                return matches[0][0]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log.warning("resolve_input_device(%r) failed: %s", query, exc)
        if time.time() >= deadline:
            break
        time.sleep(1.0)
    if last_err:
        log.warning("resolve_input_device(%r) giving up: %s", query, last_err)
    else:
        log.warning("resolve_input_device(%r): no matching input device yet", query)
    return None


def resample_int16(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resample mono int16 audio from src_rate to dst_rate.

    Many USB mics (e.g. HyperX SoloCast) won't open at 16 kHz, so we capture at
    their native rate (usually 48 kHz) and downsample here for Whisper/openWakeWord.
    """
    if src_rate == dst_rate or audio.size == 0:
        return audio.astype(np.int16)
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(src_rate, dst_rate)
        up, down = dst_rate // g, src_rate // g
        out = resample_poly(audio.astype(np.float32), up, down)
    except Exception:  # pragma: no cover - fallback to linear interp
        n_out = int(round(audio.size * dst_rate / src_rate))
        x_old = np.linspace(0, 1, audio.size, endpoint=False)
        x_new = np.linspace(0, 1, n_out, endpoint=False)
        out = np.interp(x_new, x_old, audio.astype(np.float32))
    return np.clip(out, -32768, 32767).astype(np.int16)


def input_channel_count(device) -> int:
    """Use the device's real input count. SoloCast 2 is 2ch on ALSA hw."""
    if sd is None:
        return 1
    try:
        info = sd.query_devices(device, kind="input")
        n = int(info.get("max_input_channels") or 1)
        return max(1, n)
    except Exception:
        return 1


def frames_to_mono(block) -> np.ndarray:
    """Downmix (frames, channels) to int16 mono."""
    arr = np.asarray(block)
    if arr.ndim == 2 and arr.shape[1] > 1:
        return np.mean(arr, axis=1).astype(np.int16)
    return arr.reshape(-1).astype(np.int16)



def record_until_silence(
    sample_rate: int = 16000,
    silence_timeout_s: float = 1.2,
    max_utterance_s: float = 30.0,
    input_device: int | None = None,
    capture_rate: int | None = None,
) -> np.ndarray:
    """Record from the mic until trailing silence, return int16 mono audio at
    ``sample_rate`` (16 kHz for STT).

    ``capture_rate`` is the rate the mic is actually opened at (default: same as
    ``sample_rate``). Set it to a rate your mic supports (e.g. 48000) and the audio
    is resampled down to ``sample_rate`` on the way out. Uses WebRTC VAD when the
    capture rate is VAD-compatible, otherwise an energy gate.
    """
    if sd is None:
        raise RuntimeError("sounddevice not available")

    input_device = resolve_input_device(input_device, wait_s=20.0)
    if input_device is None:
        raise RuntimeError("No microphone input device available")
    cap = capture_rate or sample_rate
    frame_ms = 30
    frame_len = int(cap * frame_ms / 1000)
    use_vad = webrtcvad is not None and cap in _VAD_RATES
    vad = webrtcvad.Vad(2) if use_vad else None
    silence_frames_needed = int(silence_timeout_s * 1000 / frame_ms)
    max_frames = int(max_utterance_s * 1000 / frame_ms)

    collected: list[np.ndarray] = []
    trailing_silence = 0
    started = False
    ring = deque(maxlen=int(0.3 * 1000 / frame_ms))  # 300ms pre-roll

    def is_speech(frame: np.ndarray) -> bool:
        if vad is not None:
            return vad.is_speech(frame.tobytes(), cap)
        return float(np.abs(frame).mean()) > 300  # energy fallback

    ch = input_channel_count(input_device)
    with sd.InputStream(
        samplerate=cap,
        channels=ch,
        dtype="int16",
        blocksize=frame_len,
        device=input_device,
    ) as stream:
        for _ in range(max_frames):
            block, _overflow = stream.read(frame_len)
            frame = frames_to_mono(block)
            speech = is_speech(frame)
            if not started:
                ring.append(frame)
                if speech:
                    started = True
                    collected.extend(ring)
                    collected.append(frame)
                continue
            collected.append(frame)
            if speech:
                trailing_silence = 0
            else:
                trailing_silence += 1
                if trailing_silence >= silence_frames_needed:
                    break

    if not collected:
        return np.zeros(0, dtype=np.int16)
    audio = np.concatenate(collected).astype(np.int16)
    return resample_int16(audio, cap, sample_rate)


def prepend_silence(path: str, lead_ms: int) -> None:
    """Add ``lead_ms`` of leading silence to a mono WAV in place.

    The Pi's HDMI (vc4) sink drops the first fraction of a clip while it spins up,
    which clips short words ("On it" -> "n it"). A small silence lead-in means the
    startup swallows silence instead of the first phoneme.
    """
    if lead_ms <= 0:
        return
    try:
        with wave.open(path, "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())
        pad = b"\x00" * (int(params.framerate * lead_ms / 1000) * params.sampwidth * params.nchannels)
        with wave.open(path, "wb") as wf:
            wf.setparams(params)
            wf.writeframes(pad + frames)
    except Exception as exc:  # pragma: no cover
        log.warning("prepend_silence failed (%s)", exc)


def peak_level(audio: np.ndarray) -> int:
    """Absolute peak sample value (0..32767) of int16 mono audio; 0 if empty.

    Used to tell "mic muted / not capturing" (near-zero peak) apart from
    "recorded fine but no speech" so we can give the user a useful hint.
    """
    if audio is None or audio.size == 0:
        return 0
    return int(np.abs(audio).max())


def play_wav(
    path: str,
    output_device: int | None = None,
    alsa_output: str | None = None,
) -> None:
    """Play a WAV file.

    If ``alsa_output`` is set (e.g. ``"plughw:0,0"``) we use ``aplay -D`` with it.
    ALSA's plug plugin auto-converts rate/format/channels, which the Pi's vc4 HDMI
    audio needs (PortAudio opens the hw device directly and often rejects the format).
    Otherwise we try sounddevice, then fall back to plain ``aplay``.
    """
    if alsa_output:
        # Large buffer + period so brief CPU stalls (whisper/openWakeWord/Hailo) don't
        # underrun the HDMI sink, which is heard as slurring / skipping. ALSA's plug
        # plugin still handles rate/format conversion for the vc4 HDMI device.
        rc = subprocess.run(
            ["aplay", "-q", "-D", alsa_output,
             "--buffer-time=500000", "--period-time=100000", path],
            check=False,
        ).returncode
        if rc == 0:
            return
        log.warning("aplay -D %s (buffered) failed (rc=%s); retrying plain", alsa_output, rc)
        rc = subprocess.run(["aplay", "-q", "-D", alsa_output, path], check=False).returncode
        if rc == 0:
            return
        log.warning("aplay -D %s failed (rc=%s); trying sounddevice", alsa_output, rc)
    try:
        if sd is not None:
            with wave.open(path, "rb") as wf:
                sr = wf.getframerate()
                data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
            sd.play(data, sr, device=output_device)
            sd.wait()
            return
    except Exception as exc:  # pragma: no cover
        log.warning("sounddevice playback failed (%s); trying aplay", exc)
    subprocess.run(["aplay", "-q", path], check=False)


def beep(output_device: int | None = None, alsa_output: str | None = None) -> None:
    """Short acknowledgement tone."""
    sr = 16000
    t = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
    tone = (0.3 * np.sin(2 * np.pi * 880 * t) * 32767).astype(np.int16)
    if alsa_output:
        out = temp_wav_path()
        write_wav(out, tone, sr)
        try:
            play_wav(out, output_device=output_device, alsa_output=alsa_output)
        finally:
            try:
                os.remove(out)
            except OSError:
                pass
        return
    if sd is None:
        return
    try:
        sd.play(tone, sr, device=output_device)
        sd.wait()
    except Exception:  # pragma: no cover
        pass


def write_wav(path: str, audio: np.ndarray, sample_rate: int) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.astype(np.int16).tobytes())


def temp_wav_path() -> str:
    return tempfile.mktemp(suffix=".wav")
