# -*- coding: utf-8 -*-
"""Inject I2V identity guidance into Jan assistants."""
from __future__ import annotations

import json
from pathlib import Path

GUIDANCE = """
### I2V identity rules (hard)
- User says 14B → workflow_id=i2v only. Never i2v_5b / i2v_5b_painter for identity-critical clips.
- Prompt = short MOTION only (1-2 sentences). Do not re-describe hair, clothes, room, or the whole sex scene — the still already has that.
- Good: Slow withdraw until tip nearly leaves her lips, then smooth reinsert; hold face and body identity; anime style.
- Bad: long erotic novels, new camera angles, photoreal, character redesign, PainterI2V for BJ/face lock.
- Default: use_painter_i2v=false. Painter/5B only if James explicitly asks for a draft or painter.
- After generate_video: if ok=false, report the error — never claim success. If saved_files exist, view_delivery_video_frame and check identity vs source before declaring done.
- Source path: list_source_images / list_delivery_media first; pass exact path (User Import or Desktop New Images).
""".strip()


def patch(path: Path, markers: list[str]) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    instr = d["instructions"]
    if "I2V identity rules" in instr:
        print(path.name, "already has identity rules")
        return
    inserted = False
    for needle in markers:
        if needle in instr:
            instr = instr.replace(needle, GUIDANCE + "\n\n" + needle, 1)
            inserted = True
            break
    if not inserted:
        if "Current date:" in instr:
            instr = instr.replace("Current date:", GUIDANCE + "\n\nCurrent date:", 1)
        else:
            instr = instr.rstrip() + "\n\n" + GUIDANCE + "\n"
    d["instructions"] = instr
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path.name, "patched, len", len(instr))


def main() -> None:
    patch(
        Path(r"D:/Jan/data/assistants/jan/assistant.json"),
        ["### Video routing (hard rules)", "### See / organize delivery media"],
    )
    patch(
        Path(r"D:/Jan/data/assistants/studio-copilot/assistant.json"),
        ["**User says 14B", "**Draft / normal video", "## Tone"],
    )


if __name__ == "__main__":
    main()
