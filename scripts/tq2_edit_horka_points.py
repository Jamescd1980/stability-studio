"""Gentle Horka point edit: active/passive + divinity (MasteryPoints). No .bak touches."""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

ACTIVE = 200
PASSIVE = 200
DIVINITY = 24  # stored as MasteryPoints in PlayerLocal


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


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    bak = saves.parent / f"SaveGames_backup_horka_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)

    local = next(saves.glob("Horka_*_Data_PlayerLocal.sav"))
    data = bytearray(local.read_bytes())
    print("EDIT Horka PlayerLocal only")
    print(" ", set_named(data, b"ActivePoints", ACTIVE))
    print(" ", set_named(data, b"PassivePoints", PASSIVE))
    print(" ", set_named(data, b"MasteryPoints", DIVINITY), "(divinity pool)")
    local.write_bytes(data)
    # Do NOT modify .bak — game manages those

    lr = local.read_bytes()
    print(
        "VERIFY",
        "Active",
        find_named_int(lr, b"ActivePoints")[1],
        "Passive",
        find_named_int(lr, b"PassivePoints")[1],
        "Divinity/MasteryPoints",
        find_named_int(lr, b"MasteryPoints")[1],
    )


if __name__ == "__main__":
    main()
