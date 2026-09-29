"""Edit Titan Quest II saves (gold, attribute AP, active/passive/mastery points)."""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

TARGET_GOLD = 250_000
TARGET_AP = 60
TARGET_ACTIVE = 25
TARGET_PASSIVE = 25
TARGET_MASTERY = 25


def find_named_int(raw: bytes, name: bytes, start: int = 0):
    """UE string length prefix includes the trailing null."""
    needle = name + b"\x00"
    idx = start
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


def set_named_int(data: bytearray, name: bytes, new_val: int) -> str:
    hit = find_named_int(bytes(data), name)
    if not hit:
        return f"FAIL {name.decode()}"
    off, old = hit
    struct.pack_into("<i", data, off, new_val)
    return f"{name.decode()} {old} -> {new_val}"


def set_gold(data: bytearray, amount: int) -> str:
    gi = data.find(b"da_item_gold")
    if gi < 0:
        return "FAIL gold stack"
    ni = data.find(b"Num\x00", gi, gi + 200)
    j = data.find(b"IntProperty\x00", ni, ni + 40)
    p = j + len(b"IntProperty\x00")
    for prefix in (
        b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
    ):
        if data[p : p + 9] == prefix:
            off = p + 9
            old = struct.unpack_from("<i", data, off)[0]
            struct.pack_into("<i", data, off, amount)
            return f"gold {old} -> {amount}"
    return "FAIL gold Num"


def edit_character(saves: Path, name: str) -> None:
    player = next(saves.glob(f"{name}_*_Data_Player.sav"))
    local = next(saves.glob(f"{name}_*_Data_PlayerLocal.sav"))
    pdata = bytearray(player.read_bytes())
    ldata = bytearray(local.read_bytes())
    print("EDIT", name)
    print(" ", set_gold(pdata, TARGET_GOLD))
    print(" ", set_named_int(pdata, b"m_CharacterAP", TARGET_AP))
    print(" ", set_named_int(ldata, b"ActivePoints", TARGET_ACTIVE))
    print(" ", set_named_int(ldata, b"PassivePoints", TARGET_PASSIVE))
    print(" ", set_named_int(ldata, b"MasteryPoints", TARGET_MASTERY))
    player.write_bytes(pdata)
    local.write_bytes(ldata)


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    bak = saves.parent / f"SaveGames_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)
    edit_character(saves, "Svanna")


if __name__ == "__main__":
    main()
