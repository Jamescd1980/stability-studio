"""Smoke-test Eric Video Prompt Expander → nari-prompt for Frieren s1b_wet."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from frieren_tease_i2v_kit import BEATS, NEG  # noqa: E402

COMFY = "http://192.168.50.57:8188"
OLLAMA = "http://127.0.0.1:11434"  # Eric runs on comfybox; node calls local Ollama
OUT = ROOT / "outputs" / "frieren_s1b_eric_smoke.json"

# Short kit prompt — Eric expands this for Wan I2V.
MOTION = BEATS["s1b_wet"]["prompt"]
POS_KW = (
    "nb_frieren, frieren, same eye size as start frame, full plump lips, "
    "both hands keep moving, no cum"
)
NEG_KW = "cum, semen, melting face, oversized eyes, thin line mouth, frozen hands"


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    # Pin nari-prompt as first /api/tags entry (Eric auto-detects models[0]).
    names: list[str] = []
    try:
        tags = get_json("http://192.168.50.57:11434/api/tags")
        names = [m["name"] for m in tags.get("models", [])]
        print("ollama tags:", names)
        if names and not names[0].startswith("nari-prompt"):
            print("WARN: first tag is not nari-prompt — Eric may pick", names[0])
    except Exception as e:
        print("WARN: could not list Ollama tags:", e)

    workflow = {
        "1": {
            "class_type": "EricVideoPromptExpander",
            "inputs": {
                "basic_prompt": (
                    "Frieren Stage1 tease beat s1b_wet (image-to-video from nude "
                    "sitting fingering still). Motion: " + MOTION
                ),
                "preset": "custom",
                "expansion_tier": "enhanced",
                "mode": "image-to-video",
                "llm_backend": "ollama",
                "api_endpoint": OLLAMA,
                "temperature": 0.65,
                "positive_keywords": POS_KW,
                "negative_keywords": NEG_KW,
                "num_variations": 1,
                "save_to_file": True,
                "filename_base": "frieren_s1b_wet_eric",
            },
        },
        # Force history to retain text (Preview Any / ShowText if present).
        "2": {
            "class_type": "PreviewAny",
            "inputs": {"source": ["1", 0]},
        },
    }

    print("queueing Eric expand…")
    print("seed motion:\n", MOTION)
    try:
        queued = post_json(f"{COMFY}/prompt", {"prompt": workflow})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print("Comfy reject:", body[:2000])
        return 1

    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        print("no prompt_id", queued)
        return 1
    print("prompt_id", prompt_id)

    for i in range(180):
        hist = get_json(f"{COMFY}/history/{prompt_id}")
        if prompt_id in hist:
            break
        time.sleep(1)
        if i % 10 == 0:
            print(f"  waiting… {i}s")
    else:
        print("timeout waiting for history")
        return 1

    entry = hist[prompt_id]
    outputs = entry.get("outputs", {}).get("1", {})
    # TEXT outputs often under "text" list
    texts = outputs.get("text") or outputs.get("string") or []
    status_msgs = entry.get("status", {})

    # Comfy stores multi-output as indexed text arrays matching output_name order
    # positive_prompt_1, positive_prompt_2, positive_prompt_3, negative_prompt, breakdown, status
    result = {
        "beat": "s1b_wet",
        "seed_motion": MOTION,
        "kit_negative": NEG,
        "prompt_id": prompt_id,
        "raw_outputs": outputs,
        "status": status_msgs,
        "ollama_tags_at_start": names,
    }

    # UI TEXT outputs: {"text": ["..."]} per output slot, keyed oddly in history
    collected: dict[str, str] = {}
    labels = [
        "positive_prompt_1",
        "positive_prompt_2",
        "positive_prompt_3",
        "negative_prompt",
        "breakdown",
        "status",
    ]
    if isinstance(texts, list) and texts:
        for label, val in zip(labels, texts):
            collected[label] = val if isinstance(val, str) else str(val)
    else:
        # Fallback: scan all output keys
        for k, v in outputs.items():
            if isinstance(v, list) and v:
                collected[k] = v[0] if isinstance(v[0], str) else json.dumps(v[0])
            elif isinstance(v, str):
                collected[k] = v

    result.update(collected)
    for label in labels:
        if label in collected:
            print(f"\n=== {label} ===\n{collected[label]}")
    if not collected:
        print("\n=== raw outputs ===\n", json.dumps(outputs, indent=2)[:3000])
        print("\n=== status ===\n", json.dumps(status_msgs, indent=2)[:2000])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT)
    return 0 if collected else 2


if __name__ == "__main__":
    raise SystemExit(main())
