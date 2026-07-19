# -*- coding: utf-8 -*-
"""Download Illustrious style/detail LoRAs for Test still recreation; sync to ComfyBox."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
KEY = (cfg.get("civitai") or {}).get("api_key") or ""
HEADERS = {"Authorization": f"Bearer {KEY}"}

LOCAL_LORA = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora")
EXTRA_LORA = Path(r"D:\Extra Models") / "LoRa's"
REMOTE = "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/"

# Known needs + nice-to-haves for style recreation canvas
# version_id -> local filename (stable, readable names)
TARGETS = [
    {
        "id": "aquaink_watercolor",
        "model_id": 2481121,
        "version_id": 2789538,
        "filename": "AquaInk_Watercolor_IL.safetensors",
        "trigger": "wc_painting",
        "use": "004 watercolor fashion sketch",
        "weight": "0.8–1.0",
    },
    {
        "id": "dramatic_color",
        "model_id": 2591071,
        "version_id": 2910712,
        "filename": "DramaticColor_IL_v1.safetensors",
        "trigger": "dramaticcolor_style",
        "use": "001/002/005 neon·crimson·grade (stack 0.2–0.4)",
        "weight": "0.3–0.6",
    },
    {
        "id": "illustrious_detailer_v2",
        "model_id": 1586731,
        "version_id": 1848589,
        "filename": "ILDetailerV2.safetensors",
        "trigger": None,
        "use": "detail / reflections if hyperdetailer soft",
        "weight": "0.6–0.8",
    },
]


def search_flare() -> dict | None:
    """Pick a popular Illustrious lens-flare / light-leak LoRA if available."""
    queries = [
        "lens flare",
        "light leak",
        "anamorphic lens flare",
        "prism light",
    ]
    best = None
    for q in queries:
        r = requests.get(
            "https://civitai.com/api/v1/models",
            headers=HEADERS,
            params={
                "query": q,
                "types": "LORA",
                "baseModels": "Illustrious",
                "limit": 8,
                "sort": "Most Downloaded",
            },
            timeout=45,
        )
        if r.status_code != 200:
            print(f"search fail {q}: {r.status_code}", flush=True)
            continue
        for m in r.json().get("items") or []:
            bms = m.get("baseModels") or []
            if "Illustrious" not in bms:
                continue
            vers = m.get("modelVersions") or []
            if not vers:
                continue
            v = vers[0]
            files = v.get("files") or []
            if not files:
                continue
            dl = int((m.get("stats") or {}).get("downloadCount") or 0)
            row = {
                "id": "lens_flare_il",
                "model_id": m["id"],
                "version_id": v["id"],
                "filename": "LensFlare_LightLeak_IL.safetensors",
                "source_name": files[0].get("name"),
                "trigger": (v.get("trainedWords") or [None])[0],
                "use": "003 suncore prism / light leak",
                "weight": "0.4–0.7",
                "title": m.get("name"),
                "downloads": dl,
            }
            title = "".join(ch if ord(ch) < 128 else "?" for ch in str(m.get("name") or ""))
            print(f"  candidate {m['id']} {title[:50]} dl={dl} v={v['id']}", flush=True)
            # Prefer explicit prism/flare/leak titles over generic "FilmFX"
            score = dl
            low = title.lower()
            if any(k in low for k in ("prism", "flare", "light leak", "lens flare")):
                score += 50_000
            if "filmfx" in low or "realism" in low:
                score -= 10_000
            row["score"] = score
            if best is None or score > best.get("score", 0):
                best = row
    return best


def download_one(version_id: int, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"skip {dest.name} ({dest.stat().st_size})", flush=True)
        return dest
    url = f"https://civitai.com/api/download/models/{version_id}"
    print(f"GET {dest.name} <- {url}", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers=HEADERS, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if total and done % (50 * 1024 * 1024) < len(chunk):
                    print(f"  ... {done // (1024 * 1024)} / {total // (1024 * 1024)} MB", flush=True)
    tmp.replace(dest)
    print(f"ok {dest.name} {dest.stat().st_size}", flush=True)
    return dest


def main() -> None:
    if not KEY:
        raise SystemExit("Missing civitai.api_key in config.yaml")

    print("Searching flare/light-leak Illustrious LoRAs…", flush=True)
    flare = search_flare()
    targets = list(TARGETS)
    if flare:
        print(f"Picked flare: {flare.get('title')} ({flare['model_id']})", flush=True)
        targets.append(flare)
    else:
        print("WARN: no Illustrious flare LoRA found — skip", flush=True)

    paths: list[Path] = []
    for t in targets:
        dest = LOCAL_LORA / t["filename"]
        download_one(int(t["version_id"]), dest)
        paths.append(dest)
        # also Extra Models LoRa's for Invoke / catalog convenience
        EXTRA_LORA.mkdir(parents=True, exist_ok=True)
        extra = EXTRA_LORA / t["filename"]
        if not extra.is_file() or extra.stat().st_size != dest.stat().st_size:
            extra.write_bytes(dest.read_bytes())
            print(f"copied Extra Models {extra.name}", flush=True)

    print("SCP -> ComfyBox…", flush=True)
    cmd = ["scp", "-o", "BatchMode=yes", *[str(p) for p in paths], REMOTE]
    subprocess.run(cmd, check=True)
    names = " ".join(p.name for p in paths)
    subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "comfybox",
            f"ls -lh /mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/{{{','.join(p.name for p in paths)}}}",
        ],
        check=False,
    )
    # simpler verify
    subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "comfybox",
            "ls -lh /mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/AquaInk* "
            "/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/DramaticColor* "
            "/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/ILDetailer* "
            "/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/LensFlare* 2>/dev/null",
        ],
        check=False,
    )

    manifest = {
        "ok": True,
        "local_dir": str(LOCAL_LORA),
        "remote_dir": "/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/",
        "loras": targets,
        "note": "Stack DramaticColor low (0.2–0.4) with character LoRAs; AquaInk for 004; Detailer if soft; Flare for 003.",
    }
    out = ROOT / "outputs" / "style_recreation_loras.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("WROTE", out, flush=True)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
