---
name: code-review-static
description: Static code/game review in the open OI workspace - report problems and inefficiencies without editing. Prefer this over qa-testing when the user says do not change / just report.
---

# Static code review (no edits)

When the user asks to go through game/coding files for problems or inefficient code **without changing anything**:

## Do

1. Infer the project from the **open OI workspace / open files** (never ask for the main filename).
2. List entrypoints and important modules with tools.
3. Read them. Search for risky patterns (bare except, hardcoded wrong paths, dead code, huge functions, sync I/O on hot paths, missing null checks, Ren'Py show/image path mismatches).
4. Return a structured report only:
   - Blockers
   - Medium
   - Nits / style
   Each item: `path:line` - issue - why

## Do not

- Do not use the system **qa-testing** skill (browser/GUI driving) unless they explicitly ask to *run* the app UI.
- Do not edit, format-on-save, or fix while reviewing.
- Do not paste tool JSON for the user - execute tools yourself.
- Do not ask for the main game file name.
