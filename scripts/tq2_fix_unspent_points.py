"""
Add unspent points correctly for TQ2 characters.

Attributes:
  m_AttributePointsMight/Agility/Knowledge/Vigor = ASSIGNED
  m_CharacterAP = TOTAL pool
  unspent = m_CharacterAP - sum(assigned)

Active/Passive:
  ActivePoints / PassivePoints = UNSPENT to assign
  InvestedPoints (many) = already spent on skills
  MasteryPoints = divinity (leave alone unless asked)

Never rewrite .bak files.
"""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

CHARS = ("Horka", "Fragarach")
ADD_UNSPENT_AP = 100
ADD_UNSPENT_ACTIVE = 100
ADD_UNSPENT_PASSIVE = 100


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


def set_at(data: bytearray, off: int, val: int) -> None:
    struct.pack_into("<i", data, off, val)


def edit_char(saves: Path, name: str) -> None:
    player = next(saves.glob(f"{name}_*_Data_Player.sav"))
    local = next(saves.glob(f"{name}_*_Data_PlayerLocal.sav"))
    pdata = bytearray(player.read_bytes())
    ldata = bytearray(local.read_bytes())

    print(f"=== {name} ===")

    assigned_keys = [
        b"m_AttributePointsMight",
        b"m_AttributePointsAgility",
        b"m_AttributePointsKnowledge",
        b"m_AttributePointsVigor",
    ]
    assigned = {}
    for key in assigned_keys:
        hit = find_named_int(bytes(pdata), key)
        if hit:
            assigned[key.decode()] = hit[1]
            print(f"  assigned {key.decode().replace('m_AttributePoints', '')} = {hit[1]}")
        else:
            print(f"  assigned {key.decode()} MISSING")
    assigned_sum = sum(assigned.values())
    print(f"  assigned sum = {assigned_sum}")

    ap_hit = find_named_int(bytes(pdata), b"m_CharacterAP")
    if not ap_hit:
        print("  FAIL m_CharacterAP")
        return
    ap_off, ap_old = ap_hit
    unspent_old = ap_old - assigned_sum
    ap_new = assigned_sum + ADD_UNSPENT_AP
    set_at(pdata, ap_off, ap_new)
    print(
        f"  m_CharacterAP (TOTAL) {ap_old} -> {ap_new}  "
        f"(unspent was ~{unspent_old}, now {ADD_UNSPENT_AP}; assigned untouched)"
    )

    for key, add in (
        (b"ActivePoints", ADD_UNSPENT_ACTIVE),
        (b"PassivePoints", ADD_UNSPENT_PASSIVE),
    ):
        hit = find_named_int(bytes(ldata), key)
        if not hit:
            print(f"  FAIL {key.decode()}")
            continue
        off, old = hit
        new = old + add
        set_at(ldata, off, new)
        print(f"  {key.decode()} (UNSPENT) {old} -> {new} (+{add})")

    div = find_named_int(bytes(ldata), b"MasteryPoints")
    print(f"  divinity/MasteryPoints left as-is ({div[1] if div else 'n/a'})")

    player.write_bytes(pdata)
    local.write_bytes(ldata)

    # verify
    pr = player.read_bytes()
    lr = local.read_bytes()
    ap = find_named_int(pr, b"m_CharacterAP")[1]
    a_sum = 0
    for key in assigned_keys:
        hit = find_named_int(pr, key)
        if hit:
            a_sum += hit[1]
    print(
        f"  VERIFY totalAP={ap} assigned={a_sum} unspent={ap - a_sum} "
        f"Active={find_named_int(lr, b'ActivePoints')[1]} "
        f"Passive={find_named_int(lr, b'PassivePoints')[1]} "
        f"Divinity={find_named_int(lr, b'MasteryPoints')[1]}"
    )


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = saves.parent / f"SaveGames_backup_unspent_{stamp}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)
    for name in CHARS:
        edit_char(saves, name)


if __name__ == "__main__":
    main()
