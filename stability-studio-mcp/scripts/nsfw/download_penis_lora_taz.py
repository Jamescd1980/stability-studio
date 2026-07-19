# -*- coding: utf-8 -*-
"""Download Taz PENISLORA Wan 2.2 I2V HIGH/LOW (+ optional CoachBate) to SM + comfybox."""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
key = cfg["civitai"]["api_key"]
headers = {"Authorization": f"Bearer {key}", "User-Agent": "stability-studio"}
dest = Path(r"D:/StabilityMatrix-win-x64/Data/Models/Lora")
dest.mkdir(parents=True, exist_ok=True)


def api_get(url: str) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def search(q: str) -> list[dict]:
    url = "https://civitai.com/api/v1/models?" + urllib.parse.urlencode(
        {"query": q, "limit": 10, "nsfw": "true"}
    )
    return api_get(url).get("items") or []


def pick_taz_versions() -> list[tuple[int, str]]:
    """Return [(version_id, dest_filename), ...] for I2V HIGH/LOW."""
    items = search("Penis Lora Blowjob Cumshot Taz")
    if not items:
        items = search("PENISLORA WAN 2.2 I2V")
    chosen: list[tuple[int, str]] = []
    for m in items:
        name = (m.get("name") or "").lower()
        if "penis" not in name and "taz" not in name:
            continue
        print(f"MODEL {m['id']} {m.get('name')}", flush=True)
        for v in m.get("modelVersions") or []:
            vn = (v.get("name") or "").lower()
            base = (v.get("baseModel") or "").lower()
            if "i2v" not in vn and "i2v" not in base and "2.2" not in vn:
                # still allow Wan Video 2.2 I2V-A14B
                if "wan video 2.2 i2v" not in base:
                    continue
            side = None
            if "high" in vn:
                side = "HIGH"
            elif "low" in vn:
                side = "LOW"
            if not side:
                continue
            files = v.get("files") or []
            fname = files[0]["name"] if files else f"PENISLORA_22_i2v_{side}.safetensors"
            # normalize dest name
            dest_name = f"PENISLORA_22_i2v_{side}_{Path(fname).name}"
            if not dest_name.lower().endswith(".safetensors"):
                dest_name = f"PENISLORA_22_i2v_{side}.safetensors"
            # Prefer shorter clean names
            dest_name = f"PENISLORA_wan22_i2v_{side.lower()}.safetensors"
            print(
                f"  ver {v['id']} {v.get('name')} trig={v.get('trainedWords')} -> {dest_name}",
                flush=True,
            )
            chosen.append((int(v["id"]), dest_name))
        if chosen:
            break
    # dedupe by side
    by_side: dict[str, tuple[int, str]] = {}
    for vid, fn in chosen:
        side = "high" if "high" in fn.lower() else "low"
        by_side[side] = (vid, fn)
    out = list(by_side.values())
    if len(out) < 2:
        raise RuntimeError(f"Could not resolve HIGH+LOW PENISLORA versions: {chosen}")
    return out


def download(version_id: int, dest_path: Path) -> Path:
    if dest_path.is_file() and dest_path.stat().st_size > 1_000_000:
        print(f"skip {dest_path.name}", flush=True)
        return dest_path
    url = f"https://civitai.com/api/download/models/{version_id}"
    print(f"GET {dest_path.name} from {url}", flush=True)
    with requests.get(url, headers=headers, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest_path.with_suffix(".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest_path)
    print(f"ok {dest_path.name} {dest_path.stat().st_size}", flush=True)
    return dest_path


def main() -> None:
    versions = pick_taz_versions()
    paths = []
    for vid, fname in versions:
        paths.append(download(vid, dest / fname))

    cmd = ["scp", *[str(p) for p in paths], "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/"]
    print("SCP", cmd, flush=True)
    subprocess.run(cmd, check=True)
    subprocess.run(
        ["ssh", "comfybox", "ls -la /mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/PENISLORA*"],
        check=True,
    )
    # write mapping for the run script
    meta = {"files": [p.name for p in paths], "trigger": "PENISLORA"}
    (ROOT / "outputs" / "penis_lora_taz.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("DONE", meta, flush=True)


if __name__ == "__main__":
    main()
