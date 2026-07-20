#!/usr/bin/env python3
"""Mine Invoke AI PNG metadata for NSFW prompting patterns."""
from __future__ import annotations

import collections
import json
import re
import struct
from pathlib import Path

ROOT = Path(r"D:\Invoke AI\outputs\images")
OUT = Path(r"D:\studio-agent\docs\invoke_nsfw_prompt_examples.md")


def png_text(path: Path) -> dict[str, str]:
    data = path.read_bytes()
    i = 8
    out: dict[str, str] = {}
    while i + 8 <= len(data):
        ln = struct.unpack(">I", data[i : i + 4])[0]
        i += 4
        typ = data[i : i + 4]
        i += 4
        chunk = data[i : i + ln]
        i += ln + 4
        if typ == b"IEND":
            break
        if typ == b"tEXt":
            k, v = chunk.split(b"\x00", 1)
            out[k.decode("latin1")] = v.decode("utf-8", "replace")
    return out


def main() -> None:
    pngs = sorted(ROOT.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"total pngs: {len(pngs)}")
    sample = pngs[:300]
    acts: collections.Counter[str] = collections.Counter()
    examples: dict[str, str] = {}
    with_meta = 0
    for p in sample:
        raw = png_text(p).get("invokeai_metadata")
        if not raw:
            continue
        with_meta += 1
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError:
            continue
        pos = meta.get("positive_prompt") or ""
        low = pos.lower()
        for a in (
            "anal sex",
            "anal penetration",
            "vaginal penetration",
            "vaginal sex",
            "doggystyle",
            "deepthroat",
            "cowgirl",
            "missionary",
            "fingering",
            "creampie",
            "blowjob",
            "facefuck",
            "shoving his cock",
            "fucks her",
        ):
            if a in low:
                acts[a] += 1
        for key in (
            "anal sex",
            "vaginal penetration",
            "deepthroat",
            "cowgirl",
            "fingering",
            "missionary",
            "blowjob",
        ):
            if key in low and key not in examples:
                examples[key] = re.sub(r"\s+", " ", pos).strip()

    print(f"with invokeai_metadata in sample: {with_meta}/{len(sample)}")
    print("ACT COUNTS")
    for k, v in acts.most_common():
        print(f"  {v:4d}  {k}")

    lines = [
        "# Invoke AI NSFW prompt examples (mined from outputs)",
        "",
        f"Source: `{ROOT}` — metadata chunk `invokeai_metadata` (not stripped).",
        "",
        "## Pattern (waijfu / Illustrious)",
        "",
        "1. Quality / aesthetic header",
        "2. Scene / lighting / room",
        "3. Style line (`anime++`, cel-shaded, …)",
        "4. **View** (`View from mans POV` — never camera)",
        "5. Character + pose description (vulgar sentence)",
        "6. Sex-act tags (`doggystyle, vaginal penetration` / `anal sex`)",
        "",
        "## Live examples",
        "",
    ]
    for k, v in examples.items():
        lines.append(f"### {k}")
        lines.append("")
        lines.append("```")
        lines.append(v[:900])
        lines.append("```")
        lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
