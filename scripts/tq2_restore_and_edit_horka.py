"""Restore SaveGames from backup, then gently edit Horka only."""
from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path

# Pre-error backup (taken immediately before the Fragarach+Horka batch edit)
BACKUP_NAME = "SaveGames_backup_20260729_121200"

AP = 60
ACTIVE = 100
PASSIVE = 100
# Leave gold alone on gentle edit unless missing / tiny
GOLD_IF_BELOW = 250_000
GOLD_THRESHOLD = 10_000


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
        return f"SKIP missing {name.decode()}"
    off, old = hit
    if old == val:
        return f"{name.decode()} already {val}"
    struct.pack_into("<i", data, off, val)
    return f"{name.decode()} {old} -> {val}"


def read_gold(raw: bytes):
    gi = raw.find(b"da_item_gold")
    if gi < 0:
        return None, None
    ni = raw.find(b"Num\x00", gi, gi + 200)
    j = raw.find(b"IntProperty\x00", ni, ni + 40)
    p = j + len(b"IntProperty\x00")
    for prefix in (
        b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
    ):
        if raw[p : p + 9] == prefix:
            off = p + 9
            return off, struct.unpack_from("<i", raw, off)[0]
    return None, None


def main() -> None:
    saved = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved"
    live = saved / "SaveGames"
    backup = saved / BACKUP_NAME
    if not backup.exists():
        raise SystemExit(f"missing backup {backup}")

    # Safety copy of current (broken) state
    broken = saved / f"SaveGames_broken_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if live.exists():
        shutil.copytree(live, broken)
        print("stashed broken live ->", broken)

    # Restore original
    shutil.rmtree(live)
    shutil.copytree(backup, live)
    print("RESTORED from", backup)

    lock = live / "SaveDataWriteLock"
    if lock.exists():
        lock.unlink()
        print("removed SaveDataWriteLock")

    player = next(live.glob("Horka_*_Data_Player.sav"))
    local = next(live.glob("Horka_*_Data_PlayerLocal.sav"))
    pdata = bytearray(player.read_bytes())
    ldata = bytearray(local.read_bytes())

    print("GENTLE EDIT Horka only")
    goff, gold = read_gold(bytes(pdata))
    if goff is not None and gold is not None and gold < GOLD_THRESHOLD:
        struct.pack_into("<i", pdata, goff, GOLD_IF_BELOW)
        print(f"  gold {gold} -> {GOLD_IF_BELOW}")
    else:
        print(f"  gold left as-is ({gold})")

    print(" ", set_named(pdata, b"m_CharacterAP", AP))
    print(" ", set_named(ldata, b"ActivePoints", ACTIVE))
    print(" ", set_named(ldata, b"PassivePoints", PASSIVE))
    # Do not touch MasteryPoints on gentle pass

    player.write_bytes(pdata)
    local.write_bytes(ldata)
    shutil.copy2(player, player.with_suffix(".bak"))
    shutil.copy2(local, local.with_suffix(".bak"))
    print("  synced Horka .bak files")

    pr = player.read_bytes()
    lr = local.read_bytes()
    _, gold = read_gold(pr)
    print(
        "VERIFY Horka",
        f"gold={gold}",
        f"AP={find_named_int(pr, b'm_CharacterAP')[1]}",
        f"Active={find_named_int(lr, b'ActivePoints')[1]}",
        f"Passive={find_named_int(lr, b'PassivePoints')[1]}",
    )
    print("Done. Fully quit TQ2, disable Steam Cloud, then load Horka.")


if __name__ == "__main__":
    main()
