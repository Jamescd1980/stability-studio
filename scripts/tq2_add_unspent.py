"""Add +100 unspent AP / active / passive. Do not touch assigned attrs or divinity."""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

CHARS = ("Horka", "Fragarach")
ADD = 100


def find_named_int(raw: bytes, name: bytes):
    needle = name + b"\x00"
    idx = 0
    while True:
        i = raw.find(needle, idx)
        if i < 0:
            return None
        if i >= 4 and struct.unpack_from("<I", raw, i - 4)[0] == len(name) + 1:
            j = raw.find(b"IntProperty\x00", i, i + 80)
            if j >= 0:
                p = j + len(b"IntProperty\x00")
                for prefix in (
                    b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
                    b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
                ):
                    if raw[p : p + 9] == prefix:
                        off = p + 9
                        return off, struct.unpack_from("<i", raw, off)[0]
        idx = i + 1


def add_named(data: bytearray, name: bytes, delta: int) -> str:
    hit = find_named_int(bytes(data), name)
    if not hit:
        return f"FAIL {name.decode()}"
    off, old = hit
    new = old + delta
    struct.pack_into("<i", data, off, new)
    return f"{name.decode()} {old} -> {new} (+{delta})"


def edit_char(saves: Path, name: str) -> None:
    player = next(saves.glob(f"{name}_*_Data_Player.sav"))
    local = next(saves.glob(f"{name}_*_Data_PlayerLocal.sav"))
    pdata = bytearray(player.read_bytes())
    ldata = bytearray(local.read_bytes())

    print(f"=== {name} ===")
    # show assigned (untouched)
    assigned = {}
    for key in (
        b"m_AttributePointsMight",
        b"m_AttributePointsAgility",
        b"m_AttributePointsKnowledge",
        b"m_AttributePointsVigor",
    ):
        hit = find_named_int(bytes(pdata), key)
        if hit:
            assigned[key.decode().replace("m_AttributePoints", "")] = hit[1]
    print(f"  assigned (unchanged): {assigned} sum={sum(assigned.values())}")

    print(" ", add_named(pdata, b"m_CharacterAP", ADD))
    print(" ", add_named(ldata, b"ActivePoints", ADD))
    print(" ", add_named(ldata, b"PassivePoints", ADD))
    div = find_named_int(bytes(ldata), b"MasteryPoints")
    print(f"  divinity/MasteryPoints left as-is ({div[1] if div else 'n/a'})")

    player.write_bytes(pdata)
    local.write_bytes(ldata)

    pr = player.read_bytes()
    lr = local.read_bytes()
    print(
        "  VERIFY AP",
        find_named_int(pr, b"m_CharacterAP")[1],
        "Active",
        find_named_int(lr, b"ActivePoints")[1],
        "Passive",
        find_named_int(lr, b"PassivePoints")[1],
    )


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = saves.parent / f"SaveGames_backup_add100_{stamp}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)
    print("NOTE: quit TQ2 before loading these characters\n")
    for name in CHARS:
        edit_char(saves, name)


if __name__ == "__main__":
    main()
