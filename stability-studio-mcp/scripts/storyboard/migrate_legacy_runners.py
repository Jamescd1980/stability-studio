#!/usr/bin/env python3
"""One-time patch: move outputs/_run_rin_*.py to legacy/ and fix bootstrap imports."""

from __future__ import annotations

import re
from pathlib import Path

MCP = Path(__file__).resolve().parents[2]
OUTPUTS = MCP / "outputs"
LEGACY = Path(__file__).resolve().parent / "legacy"

HEADER = '''#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent
sys.path.insert(0, str(_LEGACY))
from _bootstrap import setup_paths

setup_paths()
MCP_ROOT = setup_paths()
'''

OLD_ROOT = re.compile(
    r"ROOT = Path\(__file__\)\.resolve\(\)\.parents\[1\]\s*\n"
    r"sys\.path\.insert\(0, str\(ROOT\)\)\s*\n"
    r"(?:sys\.path\.insert\(0, str\(Path\(__file__\)\.resolve\(\)\.parent\)\)\s*\n)?"
    r"import rin_project_paths as P\s*\n",
    re.MULTILINE,
)


def main() -> int:
    LEGACY.mkdir(parents=True, exist_ok=True)
    moved = 0
    for src in sorted(OUTPUTS.glob("_run_rin_*.py")):
        dest = LEGACY / src.name
        text = src.read_text(encoding="utf-8")
        if OLD_ROOT.search(text):
            text = OLD_ROOT.sub(HEADER + "import rin_project_paths as P\n\n", text, count=1)
        elif "from _bootstrap import" not in text:
            # Prepend bootstrap if pattern differed
            lines = text.splitlines(keepends=True)
            if lines and lines[0].startswith("#!"):
                lines = lines[1:]
            text = HEADER + "import rin_project_paths as P\n\n" + "".join(lines)
        # Fix MCP outputs path references
        text = text.replace('ROOT / "outputs"', 'MCP_ROOT / "outputs"')
        dest.write_text(text, encoding="utf-8")
        src.unlink()
        moved += 1
        print(f"moved {src.name}")
    print(f"Done: {moved} scripts -> {LEGACY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
