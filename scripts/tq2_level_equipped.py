"""Raise equipped item m_Level to character level; scale base floats only."""
from __future__ import annotations

import os
import re
import shutil
import struct
from datetime import datetime
from pathlib import Path

from send2trash import send2trash

PREFIXES = (
    b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
    b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
)
BASE_FLOATS = (b"m_BaseArmor", b"m_BaseAttackDamage", b"m_FreeBarrier")
CHARS = ("Ains", "Ichigo")


def find_named(raw: bytes, name: bytes, typ: bytes, start: int, end: int):
    needle = name + b"\x00"
    tneedle = typ + b"\x00"
    idx = start
    while True:
        i = raw.find(needle, idx, end)
        if i < 0:
            return None
        if i >= 4 and struct.unpack_from("<I", raw, i - 4)[0] == len(name) + 1:
            j = raw.find(tneedle, i, min(i + 80, end))
            if j >= 0:
                q = j + len(tneedle)
                for pref in PREFIXES:
                    if raw[q : q + 9] == pref:
                        return q + 9
        idx = i + 1


def char_level(raw: bytes) -> int:
    off = find_named(raw, b"m_CharacterLevel", b"IntProperty", 0, len(raw))
    if off is None:
        raise SystemExit("no m_CharacterLevel")
    return struct.unpack_from("<i", raw, off)[0]


def equipped_items(raw: bytes):
    equip_from = raw.find(b"m_Equipment")
    if equip_from < 0:
        raise SystemExit("no m_Equipment")
    seen = set()
    items = []
    for m in re.finditer(rb"(da_(?:armor|weapon)_[a-z0-9_]+)\x00", raw):
        if m.start() < equip_from:
            continue
        name = m.group(1).decode()
        if "sound" in name or name in seen:
            continue
        end = min(len(raw), m.start() + 900)
        off = find_named(raw, b"m_Level", b"IntProperty", m.start(), end)
        if off is None:
            continue
        seen.add(name)
        items.append((name, m.start(), end, struct.unpack_from("<i", raw, off)[0], off))
    return equip_from, items


def patch_char(saves: Path, name: str) -> None:
    player = next(saves.glob(f"{name}_*_Data_Player.sav"))
    data = bytearray(player.read_bytes())
    raw = bytes(data)
    src = len(data)
    target = char_level(raw)
    equip_from, items = equipped_items(raw)
    print(f"EDIT {name} char_level={target} file={player.name} size={src}")
    print(f"  m_Equipment {equip_from} equipped {len(items)}")

    for iname, start, end, old_lv, lv_off in items:
        if old_lv >= target:
            print(f"  SKIP {iname} already lv {old_lv}")
            continue
        if old_lv <= 0:
            print(f"  SKIP {iname} bad level {old_lv}")
            continue
        factor = target / float(old_lv)
        struct.pack_into("<i", data, lv_off, target)
        print(f"  {iname} m_Level {old_lv} -> {target}  factor {factor:.3f}")
        for fname in BASE_FLOATS:
            foff = find_named(bytes(data), fname, b"FloatProperty", start, end)
            if foff is None:
                continue
            old = struct.unpack_from("<f", data, foff)[0]
            new = old * factor
            struct.pack_into("<f", data, foff, new)
            print(f"    {fname.decode()} {old:.3f} -> {new:.3f}")

    if len(data) != src:
        raise SystemExit("REFUSE size changed")
    player.write_bytes(data)

    raw2 = player.read_bytes()
    _, items2 = equipped_items(raw2)
    print("  VERIFY")
    for iname, start, end, lvl, _ in items2:
        armor = find_named(raw2, b"m_BaseArmor", b"FloatProperty", start, end)
        dmg = find_named(raw2, b"m_BaseAttackDamage", b"FloatProperty", start, end)
        print(
            f"    {iname} lvl {lvl}"
            f" armor={None if armor is None else round(struct.unpack_from('<f', raw2, armor)[0], 2)}"
            f" dmg={None if dmg is None else round(struct.unpack_from('<f', raw2, dmg)[0], 2)}"
        )


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    for n in ("Saving.sav", "SaveDataWriteLock"):
        p = saves / n
        if p.exists():
            send2trash(str(p))
            print("BIN", n)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = saves.parent / f"SaveGames_backup_ains_ichigo_gearlevel_{stamp}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)
    for name in CHARS:
        patch_char(saves, name)
    print(".bak / affixes / inventory not touched")


if __name__ == "__main__":
    main()
