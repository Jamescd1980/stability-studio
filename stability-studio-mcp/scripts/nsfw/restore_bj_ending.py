# -*- coding: utf-8 -*-
"""Restore recycled BJ ending clips and rebuild final: bobbing → bridge → oralcream → facial_00001."""
from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.video_utils import concat_videos, probe_video

DELIVERY = Path(r"D:\ComfyBox Images and Videos")
VIDEO = DELIVERY / "Video"
ARCHIVE = DELIVERY / "final" / "bj_closeup_oral_creampie"
OUT = ARCHIVE / "studio_agent_wan22_sq_oralcream_facial_final.mp4"

# Prefer this ending order (continuity into tip-hold oralcream):
WANT = [
    "studio_agent_wan22_sq_bobbing19.mp4",
    "studio_agent_wan22_sq25_cream_00001.mp4",  # bridge from bobbing
    "studio_agent_wan22_sq25_money_00001.mp4",  # almost-out
    "studio_agent_wan22_sq25_oralcream_00001.mp4",
    "studio_agent_wan22_sq25_facial_00001.mp4",
]

# Minimum acceptable if cream/money missing
MINIMAL = [
    "studio_agent_wan22_sq_bobbing19.mp4",
    "studio_agent_wan22_sq25_oralcream_00001.mp4",
    "studio_agent_wan22_sq25_facial_00001.mp4",
]


def _recycle_roots() -> list[Path]:
    roots: list[Path] = []
    for drive in ("C:\\", "D:\\"):
        base = Path(drive) / "$Recycle.Bin"
        if base.is_dir():
            try:
                roots.extend([p for p in base.iterdir() if p.is_dir()])
            except PermissionError:
                pass
    return roots


def _parse_i_file(ipath: Path) -> str | None:
    """Return original path string from a $I* recycle metadata file, if readable."""
    try:
        data = ipath.read_bytes()
    except OSError:
        return None
    if len(data) < 28:
        return None
    # Win Vista+ $I format: version(8) + size(8) + filetime(8) + path len(4) + path utf16
    try:
        version = struct.unpack_from("<Q", data, 0)[0]
        if version == 2:
            path_len = struct.unpack_from("<I", data, 24)[0]
            raw = data[28 : 28 + path_len * 2]
            return raw.decode("utf-16le").rstrip("\x00")
    except Exception:
        pass
    # fallback scan
    text = data.decode("utf-16le", errors="ignore")
    if "ComfyBox" in text or "studio_agent" in text:
        # grab from drive letter
        for marker in ("D:\\", "C:\\"):
            idx = text.find(marker)
            if idx >= 0:
                chunk = text[idx:].split("\x00")[0].strip()
                if chunk:
                    return chunk
    return None


def restore_from_recycle(wanted_names: set[str], dest_dir: Path) -> dict[str, Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    for root in _recycle_roots():
        try:
            i_files = list(root.glob("$I*"))
        except PermissionError:
            continue
        for ipath in i_files:
            orig = _parse_i_file(ipath)
            if not orig:
                continue
            name = Path(orig).name
            if name not in wanted_names or name in found:
                continue
            rpath = ipath.parent / ("$R" + ipath.name[2:])
            if not rpath.is_file():
                # sometimes extension kept on $R
                alts = list(ipath.parent.glob("$R" + ipath.name[2:] + "*"))
                rpath = alts[0] if alts else rpath
            if not rpath.is_file():
                print(f"META only (no $R): {name}", flush=True)
                continue
            dest = dest_dir / name
            shutil.copy2(rpath, dest)
            found[name] = dest
            print(f"RESTORED {name} ({dest.stat().st_size} bytes) from {orig}", flush=True)
    return found


def main() -> None:
    wanted = set(WANT)
    # also restore archive keepers if missing
    wanted |= {
        "studio_agent_wan22_sq_00001.mp4",
        "studio_agent_wan22_sq_12s.mp4",
        "studio_agent_wan22_widefix_00001.mp4",
    }

    staging = VIDEO / "_restored_ending"
    staging.mkdir(parents=True, exist_ok=True)

    # Already in archive?
    have: dict[str, Path] = {}
    for name in wanted:
        for folder in (ARCHIVE, VIDEO, staging):
            p = folder / name
            if p.is_file() and p.stat().st_size > 1000:
                have[name] = p
                break

    missing = wanted - set(have)
    print("have", sorted(have), flush=True)
    print("missing", sorted(missing), flush=True)
    if missing:
        restored = restore_from_recycle(missing, staging)
        have.update(restored)

    # Pick sequence
    seq_names = WANT if all(n in have for n in WANT) else None
    if seq_names is None:
        if all(n in have for n in MINIMAL):
            seq_names = MINIMAL
            print("WARN: cream/money bridge missing — using bobbing+oralcream+facial only", flush=True)
        else:
            raise FileNotFoundError(
                f"Cannot rebuild ending; still missing: {sorted(wanted - set(have))}"
            )

    paths = [have[n] for n in seq_names]
    for p in paths:
        print(f"  + {p.name} ({probe_video(p)['duration_sec']:.2f}s)", flush=True)

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    concat_videos(paths, OUT)
    video_copy = VIDEO / OUT.name
    shutil.copy2(OUT, video_copy)

    # Refresh archive copies of ending pieces
    for n in seq_names:
        shutil.copy2(have[n], ARCHIVE / n)

    summary = {
        "ok": True,
        "final": str(OUT),
        "video_copy": str(video_copy),
        "duration_sec": probe_video(OUT)["duration_sec"],
        "sequence": seq_names,
        "note": "Ending = first oral creampie + first failed facial; bridge cream/money if restored.",
    }
    (ROOT / "outputs" / "bj_restore_oral_facial_ending.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("DONE", json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
