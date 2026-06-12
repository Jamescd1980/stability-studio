# Stability Studio onboarding pack

Download or clone the **studio-agent** repo, open it in **Cursor** or **Open Interpreter**, and let your AI assistant read this folder.

## What this is

An **MCP workflow** — not a one-click app. The assistant uses MCP tools to drive **ComfyUI** (and optionally **Wan2GP**) on your PC. You answer simple questions; the agent runs checks and tells you the next step.

## Start here (humans)

1. Clone the repo and run `install.ps1` from the repo root.
2. Install **Stability Matrix** + **ComfyUI** when you’re ready for images (Tier 1).
3. Open the repo in Cursor; enable the **stability-studio** MCP server.
4. Tell the agent: *“Help me set up Stability Studio”* or *“I want to generate anime images.”*

## Start here (agents)

1. Read **`ONBOARDING.md`** and **`CHECKLIST.yaml`**.
2. Call **`get_onboarding_context`** if MCP is connected.
3. Ask discovery questions (goal, GPU, ComfyUI experience).
4. Follow the tier path; do not skip to Wan2GP on 24 GB+ machines.

## Files

| File | Purpose |
|------|---------|
| `ONBOARDING.md` | Conversational playbook for agents |
| `CHECKLIST.yaml` | Tiers, tools, VRAM rules, install order |
| `TROUBLESHOOTING.md` | Common failures in plain language |
| `config.yaml.template` | Config starter — copy to `stability-studio-mcp/config.yaml` |
| `PROJECT.template/` | Empty project folder layout for storyboards |
| `examples/rin/` | Finished Rin storyboard reference |

## Difficulty tiers

| Tier | Goal |
|------|------|
| 0 | Browse examples — no GPU |
| 1 | Still images |
| 2 | Draft video (ComfyUI) |
| 3 | Storyboard + audio + splice |
| 4 | Hero motion / lip sync (Wan2GP — optional, mainly ≤16 GB) |

**≥ 24 GB VRAM:** ComfyUI only — do not offer Wan2GP unless the user is stuck.
