from __future__ import annotations

import os
import re
import struct
from pathlib import Path

jpath = Path(
    r"D:/SteamLibrary/steamapps/common/Titan Quest II/TQ2/CookedData/JsonMetaDataCache.json"
)
j = jpath.read_text(encoding="utf-8", errors="replace")
items = sorted(set(re.findall(r'/JsonData/TQ2/Items/[^"]+', j)))
print("catalog divinity-ish items:")
for it in items:
    low = it.lower()
    if "divin" in low or "divine" in low or ("point" in low and "god" in low):
        print(" ", it)

saves = Path(os.environ["LOCALAPPDATA"]) / "TQ2" / "Saved" / "SaveGames"
pr = next(saves.glob("Horka_*_Data_Player.sav")).read_bytes()
lr = next(saves.glob("Horka_*_Data_PlayerLocal.sav")).read_bytes()
hr = next(saves.glob("Horka_*_Header.sav")).read_bytes()

print("\nHorka da_item_ hits of interest:")
for it in sorted(set(re.findall(rb"da_item_[a-z0-9_]+", pr))):
    s = it.decode()
    if any(k in s for k in ("divin", "divine", "god", "boon", "feather", "curr")):
        print(" ", s)

print("\nstring probes:")
for pat in [
    b"DivinityPoint",
    b"DivinityPoints",
    b"DivinePoints",
    b"m_Divinity",
    b"DivineCore",
    b"divine_core",
    b"AvailableDivinity",
    b"UnspentDivinity",
    b"Divinity",
    b"Divine",
]:
    print(pat, "P", pr.find(pat), "L", lr.find(pat), "H", hr.find(pat))

# dump all IntProperty names around end of PlayerLocal (skill area)
print("\nPlayerLocal IntProperty names:")
for m in re.finditer(rb"([A-Za-z][A-Za-z0-9_]{2,60})\x00\x0c\x00\x00\x00IntProperty\x00", lr):
    name = m.group(1).decode()
    if any(k in name.lower() for k in ("point", "divin", "divine", "skill", "mastery", "active", "passive")):
        # value
        p = m.end()
        val = None
        for prefix in (
            b"\x04\x00\x00\x00\x00\x00\x00\x00\x00",
            b"\x00\x00\x00\x00\x04\x00\x00\x00\x00",
        ):
            if lr[p : p + 9] == prefix:
                val = struct.unpack_from("<i", lr, p + 9)[0]
                break
        print(f"  {name} = {val}")
