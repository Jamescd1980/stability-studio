"""Set Horka gold to 500k. Touch .sav only — never .bak."""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

GOLD = 500_000


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = saves.parent / f"SaveGames_backup_horka_gold_{stamp}"
    shutil.copytree(saves, bak)
    print("BACKUP", bak)

    player = next(saves.glob("Horka_*_Data_Player.sav"))
    data = bytearray(player.read_bytes())
    gi = data.find(b"da_item_gold")
    if gi < 0:
        raise SystemExit("no gold stack")
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
            struct.pack_into("<i", data, off, GOLD)
            print(f"gold {old} -> {GOLD}")
            break
    else:
        raise SystemExit("gold parse fail")

    player.write_bytes(data)
    raw = player.read_bytes()
    gi = raw.find(b"da_item_gold")
    ni = raw.find(b"Num\x00", gi, gi + 200)
    j = raw.find(b"IntProperty\x00", ni, ni + 40)
    p = j + len(b"IntProperty\x00")
    for prefix in (
        b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
    ):
        if raw[p : p + 9] == prefix:
            print("VERIFY", struct.unpack_from("<i", raw, p + 9)[0])
            break


if __name__ == "__main__":
    main()
