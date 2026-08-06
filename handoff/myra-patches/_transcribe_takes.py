from pathlib import Path
import sys
import wave

import numpy as np

sys.path.insert(0, str(Path.home() / "studio-edge"))
from studio_edge import audio as audio_mod
from studio_edge.config import load_config
from studio_edge.stt import build_transcriber

cfg = load_config()
stt = build_transcriber(cfg)
out = Path.home() / "studio-recordings" / "transcripts.txt"
lines = []
for p in sorted((Path.home() / "studio-recordings").glob("take_*.wav")):
    with wave.open(str(p), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    if sr != 16000:
        audio = audio_mod.resample_int16(audio, sr, 16000)
        sr = 16000
    text = (stt.transcribe(audio, sr) or "").replace("\n", " ").strip()
    line = f"{p.name}|{text}"
    print(line, flush=True)
    lines.append(line)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("WROTE", out, flush=True)
