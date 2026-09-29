"""Read-only: find which field is Ichigo's 6 unspent divinity."""
from __future__ import annotations

import os
import re
import struct
from pathlib import Path

SAVES = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
PREFIXES = (
    b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
    b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
)


def ints_named(raw: bytes, name: bytes):
    needle = name + b"\x00"
    idx = 0
    hits = []
    while True:
        i = raw.find(needle, idx)
        if i < 0:
            break
        declared_ok = i >= 4 and struct.unpack_from("<I", raw, i - 4)[0] == len(name) + 1
        j = raw.find(b"IntProperty\x00", i, i + 90)
        val = None
        off = None
        if j >= 0:
            p = j + len(b"IntProperty\x00")
            for prefix in PREFIXES:
                if raw[p : p + 9] == prefix:
                    off = p + 9
                    val = struct.unpack_from("<i", raw, off)[0]
                    break
        hits.append((i, declared_ok, val, off))
        idx = i + 1
    return hits


def nearby_names(raw: bytes, pos: int, radius: int = 180) -> str:
    chunk = raw[max(0, pos - radius) : pos + radius]
    names = re.findall(rb"[A-Za-z][A-Za-z0-9_]{2,50}", chunk)
    return " ".join(n.decode() for n in names[:24])


def all_int_props(raw: bytes):
    out = []
    for m in re.finditer(
        rb"([A-Za-z][A-Za-z0-9_]{2,60})\x00.{0,8}IntProperty\x00", raw
    ):
        name = m.group(1).decode()
        p = m.end()
        val = None
        for prefix in PREFIXES:
            if raw[p : p + 9] == prefix:
                val = struct.unpack_from("<i", raw, p + 9)[0]
                break
        if val is None:
            continue
        out.append((m.start(), name, val))
    return out


def dump_char(name: str) -> None:
    files = {
        "Player": next(SAVES.glob(f"{name}_*_Data_Player.sav")),
        "Local": next(SAVES.glob(f"{name}_*_Data_PlayerLocal.sav")),
        "Header": next(SAVES.glob(f"{name}_*_Header.sav")),
    }
    print("=" * 70)
    print(name)
    for label, path in files.items():
        raw = path.read_bytes()
        print(f"\n-- {label} {path.name} size={len(raw)} --")
        for key in (
            b"MasteryPoints",
            b"InvestedMasteryPoints",
            b"AvailableMasteryPoints",
            b"UnspentMasteryPoints",
            b"DivinityPoints",
            b"Divinity",
            b"DivinePoints",
        ):
            hits = ints_named(raw, key)
            if not hits:
                continue
            print(f"  {key.decode()} x{len(hits)}")
            for i, ok, val, off in hits:
                print(f"    off={i} declared={ok} val={val}  ctx={nearby_names(raw, i)}")

        print("  IntProperties whose value is 6:")
        sixes = [(p, n, v) for p, n, v in all_int_props(raw) if v == 6]
        # de-dupe consecutive same name
        seen = set()
        for p, n, v in sixes:
            tag = (n, v, p // 50)
            if (n, v) in seen and n in (
                "InvestedPoints",
                "Num",
                "Count",
            ):
                continue
            seen.add((n, v))
            print(f"    {n}={v} at {p}")

        print("  point/mastery/divin IntProperties (all values):")
        for p, n, v in all_int_props(raw):
            low = n.lower()
            if any(k in low for k in ("point", "mastery", "divin", "divine", "ichor")):
                print(f"    {n}={v} at {p}")


def main() -> None:
    for name in ("Ichigo", "Ains", "Svanna", "Horka"):
        dump_char(name)


if __name__ == "__main__":
    main()
