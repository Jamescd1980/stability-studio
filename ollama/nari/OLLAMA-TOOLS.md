# Nari tools vs Ollama “plugins”

Ollama has **no plugin/extension API** for attaching tools to a model. Tools are always provided by the **client** on each chat request (OpenAI-compatible `tools=[]`), or via MCP.

## What we use

| Layer | Role |
|-------|------|
| **Stability Studio MCP** | Real tools: `read_studio_doc`, `list_studio_docs`, `search_studio_docs`, `lookup_character_identity`, generate_*, Wan checklist, … |
| **Open Interpreter + Nari skill** | Tool-calling client; MCP wired in `configure_open_interpreter.py` |
| **Cursor** | Same MCP namespace |
| **`oi_do.py`** | Shell fallback when chat has no tools: `docs` / `read` / `search` / `who eris` |
| **Modelfile SYSTEM** | Tells Nari *which* tools to call and that Eris is baked into waijfu |

## Do not build

A fake “Ollama plugin” that mutates weights. Keep knowledge in docs + catalog; keep actions in MCP.

## Voice (Myra → Nari)

Still chat-only unless Myra is taught to forward MCP/tool results. Prefer: Myra routes create asks to Windows OI/Cursor Nari, or extend `ask_nari` later to call `oi_do` / MCP.
