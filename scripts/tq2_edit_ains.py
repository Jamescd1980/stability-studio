"""Ains: 3M gold, 250 active, 250 passive, 500 unspent attribute points.

Same field map as Fragarach/Horka edits:
  gold = da_item_gold Num in Data_Player
  unspent AP = m_CharacterAP - sum(assigned attrs)
  ActivePoints / PassivePoints in Data_PlayerLocal
  MasteryPoints (divinity) left alone
"""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

CHAR = "Ains"
GOLD = 3_000_000
ACTIVE = 250
PASSIVE = 250
UNSPENT_AP = 500


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


def set_named(data: bytearray, name: bytes, val: int) -> str:
    hit = find_named_int(bytes(data), name)
    if not hit:
        return f"FAIL {name.decode()}"
    off, old = hit
    struct.pack_into("<i", data, off, val)
    return f"{name.decode()} {old} -> {val}"


def set_gold(data: bytearray, amount: int) -> str:
    gi = data.find(b"da_item_gold")
    if gi < 0:
        return "FAIL no gold stack — earn a bit of gold in-game first"
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


def read_gold(raw: bytes) -> int | None:
    gi = raw.find(b"da_item_gold")
    if gi < 0:
        return None
    ni = raw.find(b"Num\x00", gi, gi + 200)
    j = raw.find(b"IntProperty\x00", ni, ni + 40)
    p = j + len(b"IntProperty\x00")
    for prefix in (
        b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
    ):
        if raw[p : p + 9] == prefix:
            return struct.unpack_from("<i", raw, p + 9)[0]
    return None


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = saves.parent / f"SaveGames_backup_ains_{stamp}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)

    player = next(saves.glob(f"{CHAR}_*_Data_Player.sav"))
    local = next(saves.glob(f"{CHAR}_*_Data_PlayerLocal.sav"))
    pdata = bytearray(player.read_bytes())
    ldata = bytearray(local.read_bytes())

    assigned_keys = [
        b"m_AttributePointsMight",
        b"m_AttributePointsAgility",
        b"m_AttributePointsKnowledge",
        b"m_AttributePointsVigor",
    ]
    assigned_sum = 0
    print(f"EDIT {CHAR} (.sav only)")
    for key in assigned_keys:
        hit = find_named_int(bytes(pdata), key)
        if hit:
            print(f"  assigned {key.decode().replace('m_AttributePoints', '')} = {hit[1]} (unchanged)")
            assigned_sum += hit[1]
        else:
            print(f"  assigned {key.decode().replace('m_AttributePoints', '')} = n/a")
    print(f"  assigned sum = {assigned_sum}")

    print(" ", set_gold(pdata, GOLD))
    print(" ", set_named(pdata, b"m_CharacterAP", assigned_sum + UNSPENT_AP))
    print(" ", set_named(ldata, b"ActivePoints", ACTIVE))
    print(" ", set_named(ldata, b"PassivePoints", PASSIVE))
    div = find_named_int(bytes(ldata), b"MasteryPoints")
    print(f"  divinity/MasteryPoints left as-is ({div[1] if div else 'n/a'})")

    player.write_bytes(pdata)
    local.write_bytes(ldata)

    pr = player.read_bytes()
    lr = local.read_bytes()
    ap = find_named_int(pr, b"m_CharacterAP")[1]
    print(
        "VERIFY gold",
        read_gold(pr),
        "totalAP",
        ap,
        "unspentAP",
        ap - assigned_sum,
        "Active",
        find_named_int(lr, b"ActivePoints")[1],
        "Passive",
        find_named_int(lr, b"PassivePoints")[1],
        "Divinity",
        find_named_int(lr, b"MasteryPoints")[1],
    )


if __name__ == "__main__":
    main()
