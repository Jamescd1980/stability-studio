"""Edit TQ2 characters: gold, AP, active/passive points; sync .bak files."""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

GOLD = 250_000
AP = 60
ACTIVE = 100
PASSIVE = 100
CHARS = ("Fragarach", "Horka")


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
        return "FAIL no gold stack"
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


def edit_char(saves: Path, name: str) -> None:
    player = next(saves.glob(f"{name}_*_Data_Player.sav"))
    local = next(saves.glob(f"{name}_*_Data_PlayerLocal.sav"))
    pdata = bytearray(player.read_bytes())
    ldata = bytearray(local.read_bytes())

    print(f"EDIT {name}")
    print(" ", set_gold(pdata, GOLD))
    print(" ", set_named(pdata, b"m_CharacterAP", AP))
    print(" ", set_named(ldata, b"ActivePoints", ACTIVE))
    print(" ", set_named(ldata, b"PassivePoints", PASSIVE))

    player.write_bytes(pdata)
    local.write_bytes(ldata)

    # Keep .bak in sync so a failed load does not roll back to pre-edit
    for sav in (player, local):
        bak = sav.with_suffix(".bak")
        shutil.copy2(sav, bak)
        print(f"  synced {bak.name}")


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    lock = saves / "SaveDataWriteLock"
    if lock.exists():
        print("WARNING SaveDataWriteLock present — quit TQ2 fully before loading")

    bak_root = saves.parent / f"SaveGames_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(saves, bak_root)
    print("BACKUP", bak_root)

    for name in CHARS:
        edit_char(saves, name)

    print("VERIFY")
    for name in CHARS:
        pr = next(saves.glob(f"{name}_*_Data_Player.sav")).read_bytes()
        lr = next(saves.glob(f"{name}_*_Data_PlayerLocal.sav")).read_bytes()
        gi = pr.find(b"da_item_gold")
        ni = pr.find(b"Num\x00", gi, gi + 200)
        j = pr.find(b"IntProperty\x00", ni, ni + 40)
        p = j + len(b"IntProperty\x00")
        gold = None
        for prefix in (
            b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
            b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
        ):
            if pr[p : p + 9] == prefix:
                gold = struct.unpack_from("<i", pr, p + 9)[0]
                break
        print(
            f"  {name}: gold={gold} AP={find_named_int(pr, b'm_CharacterAP')[1]} "
            f"Active={find_named_int(lr, b'ActivePoints')[1]} "
            f"Passive={find_named_int(lr, b'PassivePoints')[1]}"
        )


if __name__ == "__main__":
    main()
