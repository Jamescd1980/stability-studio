"""After BJ06/BJ07 I2V redos finish, promote into post-renumber slots.

Live gens still write:
  BJ06.mp4 = new lick
  BJ07.mp4 = new clean

Final layout:
  BJ06 <- BJ06_from_old05.mp4 (old BJ05)
  BJ07 <- lick (from BJ06.mp4 after I2V)
  BJ08 <- clean (from BJ07.mp4 after I2V)
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

ROOT = Path(r"D:\ComfyBox Images and Videos\Video\Frieren")
BAK = sorted(ROOT.glob("_renumber_backup_*"))[-1]
OLD06_SIZE = (BAK / "BJ06.mp4").stat().st_size
OLD07_SIZE = (BAK / "BJ07.mp4").stat().st_size
START_MTIME = time.time()


def wait_new_stable(path: Path, old_size: int, timeout: float = 7200) -> bool:
    """Wait until file is rewritten after this script started, then size-stable."""
    print(
        f"waiting NEW stable {path.name} (reject size={old_size}, mtime>{START_MTIME:.0f})",
        flush=True,
    )
    t0 = time.time()
    last = -1
    stable = 0
    while time.time() - t0 < timeout:
        if path.is_file():
            st = path.stat()
            sz = st.st_size
            # Must be newer than watcher start AND not the pre-redo snapshot size
            if st.st_mtime > START_MTIME and sz != old_size and sz > 200_000:
                age = time.time() - st.st_mtime
                if sz == last and age > 8:
                    stable += 1
                    if stable >= 4:
                        print(f"  ready {path.name} size={sz}", flush=True)
                        return True
                else:
                    stable = 0
                last = sz
        time.sleep(2)
    return False


def main() -> int:
    lick_live = ROOT / "BJ06.mp4"
    clean_live = ROOT / "BJ07.mp4"
    old05 = ROOT / "BJ06_from_old05.mp4"
    lick_hold = ROOT / "BJ07_lick_pending.mp4"

    if not wait_new_stable(lick_live, OLD06_SIZE):
        print("TIMEOUT lick", flush=True)
        return 2
    shutil.copy2(lick_live, lick_hold)
    print(f"held lick -> {lick_hold.name} ({lick_hold.stat().st_size})", flush=True)

    if not wait_new_stable(clean_live, OLD07_SIZE):
        print("TIMEOUT clean", flush=True)
        return 2

    shutil.copy2(clean_live, ROOT / "BJ08.mp4")
    print("BJ08.mp4 <- clean redo", flush=True)
    shutil.copy2(lick_hold, ROOT / "BJ07.mp4")
    print("BJ07.mp4 <- lick redo", flush=True)
    if old05.exists():
        shutil.copy2(old05, ROOT / "BJ06.mp4")
        print("BJ06.mp4 <- old BJ05", flush=True)

    print("Renumber promote DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
