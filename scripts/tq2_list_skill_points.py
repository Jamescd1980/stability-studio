"""List invested points per mastery skill/passive from TQ2 PlayerLocal saves."""
from __future__ import annotations

import os
import re
import struct
from pathlib import Path


def parse_char(saves: Path, name: str) -> None:
    lr = next(saves.glob(f"{name}_*_Data_PlayerLocal.sav")).read_bytes()
    print("=" * 60)
    print(name)

    mastery_hits = list(
        re.finditer(rb"/JsonData/TQ2/Masteries/(da_mastery_[a-z0-9_]+)\x00", lr)
    )
    for mi, m in enumerate(mastery_hits):
        mastery = m.group(1).decode().replace("da_mastery_", "")
        start = m.start()
        end = mastery_hits[mi + 1].start() if mi + 1 < len(mastery_hits) else len(lr)
        chunk = lr[start:end]

        imp = None
        j = chunk.find(b"\x16\x00\x00\x00InvestedMasteryPoints\x00")
        if j >= 0:
            p = chunk.find(b"IntProperty\x00", j, j + 80) + len(b"IntProperty\x00")
            for prefix in (
                b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
                b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
            ):
                if chunk[p : p + 9] == prefix:
                    imp = struct.unpack_from("<i", chunk, p + 9)[0]
                    break
        print(f"\n  Mastery: {mastery}  (divinity invested into mastery: {imp})")

        positions: list[tuple[int, int]] = []
        idx = 0
        while True:
            i = chunk.find(b"InvestedPoints\x00", idx)
            if i < 0:
                break
            if i >= 4 and struct.unpack_from("<I", chunk, i - 4)[0] == len(
                b"InvestedPoints"
            ) + 1:
                j = chunk.find(b"IntProperty\x00", i, i + 80)
                p = j + len(b"IntProperty\x00")
                val = None
                for prefix in (
                    b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
                    b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
                ):
                    if chunk[p : p + 9] == prefix:
                        val = struct.unpack_from("<i", chunk, p + 9)[0]
                        break
                if val is not None:
                    positions.append((i, val))
            idx = i + 1

        print("  Skills / passives with invested points:")
        any_nz = False
        for n, (pos, val) in enumerate(positions):
            if not val:
                continue
            any_nz = True
            stop = positions[n + 1][0] if n + 1 < len(positions) else len(chunk)
            region = chunk[pos:stop]
            before = chunk[:pos]
            last_active = before.rfind(b"ActiveAbilities")
            last_passive = before.rfind(b"PassiveAbilities")
            kind = "passive" if last_passive > last_active else "active"

            skill = None
            mpath = re.search(rb"/Masteries/[A-Za-z]+/([A-Za-z]+)/", region)
            if mpath:
                skill = mpath.group(1).decode()
            ppath = re.search(rb"/Passives/([A-Za-z]+)/", region)
            if ppath and kind == "passive":
                skill = ppath.group(1).decode()

            mods = []
            for pm in re.findall(
                rb"/Game/TQ2/Data/Abilities/Player/[^\x00]+\.([A-Za-z0-9_]+)_C\x00",
                region,
            ):
                s = pm.decode()
                for pref in (
                    "bp_gam_player_ea_",
                    "bp_gam_player_fo_",
                    "bp_bge_player_ea_passive_",
                    "bp_bge_player_fo_passive_",
                    "bp_gam_player_generic_",
                    "bp_bge_player_",
                ):
                    if s.startswith(pref):
                        s = s[len(pref) :]
                if s not in mods:
                    mods.append(s)

            label = skill or (mods[0] if mods else "?")
            print(f"    [{kind:7}] {label}: {val} pts")
            if mods:
                print(f"             -> {', '.join(mods[:5])}")
        if not any_nz:
            print("    (none)")


def main() -> None:
    saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
    for char in ("Horka", "Fragarach"):
        parse_char(saves, char)


if __name__ == "__main__":
    main()
