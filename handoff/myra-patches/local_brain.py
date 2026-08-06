"""Local Ollama brain for Myra (room assistant) with tool calling."""
from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any

import requests

from . import room_tools

log = logging.getLogger("studio_edge.local_brain")

DEFAULT_SYSTEM = """
You are Myra, the room gofor for a visual-novel author.
You run on a Raspberry Pi. Keep answers short for text-to-speech: 1 to 3 plain sentences.
No markdown, bullets, emoji, or code.

You own the room: weather, headlines, date/time, timers, notes, recordings, web look-ups, reading aloud, display.
Use ask_nari for create / refine / Forge / clip / Comfy / Wan.
Use ask_orla for open / display / upscale / RIFE / interp on the main PC.
Prefer tools over guessing. Never invent the time or job results.
When the user says make a recording or start recording, call start_recording.
""".strip()


class LocalBrain:
    """OpenAI-compatible client aimed at Ollama on localhost."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        model: str = "myra-gofor",
        api_key: str = "ollama",
        system_prompt: str = "",
        timeout_s: int = 90,
        history_turns: int = 4,
        connect_timeout_s: float = 3.0,
        tools_enabled: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or "ollama"
        self.system_prompt = (system_prompt or DEFAULT_SYSTEM).strip()
        self.timeout_s = timeout_s
        self.connect_timeout_s = connect_timeout_s
        self.tools_enabled = tools_enabled
        self.history: deque[dict[str, Any]] = deque(maxlen=history_turns * 2)
        # Set by ask() when a tool needs a specific TTS path (e.g. book narrate).
        self.last_tts_quality: str = "piper"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def is_up(self) -> bool:
        try:
            r = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=(self.connect_timeout_s, 5),
            )
            return r.status_code < 500
        except requests.RequestException:
            return False

    def _chat(self, messages: list[dict[str, Any]], *, use_tools: bool) -> dict[str, Any]:
        # Prefer Ollama native /api/chat so think:false actually disables Qwen3
        # hidden reasoning (OpenAI-compat /v1 often ignores it → empty content + timeouts).
        native_root = self.base_url
        if native_root.endswith("/v1"):
            native_root = native_root[: -len("/v1")]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.5},
        }
        if use_tools and self.tools_enabled:
            payload["tools"] = room_tools.TOOL_DEFINITIONS
        r = requests.post(
            f"{native_root}/api/chat",
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=(self.connect_timeout_s, self.timeout_s),
        )
        r.raise_for_status()
        data = r.json()
        msg = data.get("message")
        if not isinstance(msg, dict):
            raise ValueError(f"unexpected ollama chat response: {data!r}")
        return msg

    def ask(self, user_text: str, cfg: dict, jan_brain=None, orla_brain=None) -> str:
        """Chat with optional tool rounds. Returns speakable text."""
        self.last_tts_quality = "piper"
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(list(self.history))
        messages.append({"role": "user", "content": user_text})

        try:
            msg = self._chat(messages, use_tools=True)
        except requests.RequestException as exc:
            log.error("Local LLM request failed: %s", exc)
            return "I couldn't reach my local brain. Is Ollama running?"
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            log.error("Unexpected local LLM response: %s", exc)
            return "I got a confusing answer from my local model."

        # Tool-call loop (cap rounds so a confused model can't spin forever)
        used_read_aloud = False
        last_read_text = ""
        for _ in range(4):
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                break
            messages.append(msg)
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}
                log.info("Tool %s(%s)", name, args)
                result = room_tools.run_tool(
                    name, args, cfg, jan_brain, orla_brain=orla_brain
                )
                if name == "read_aloud":
                    used_read_aloud = True
                    last_read_text = str(result or "")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", name),
                        "name": name,
                        "content": result,
                    }
                )
            # Book text must go straight to Kokoro — don't let the LLM rewrite/summarize it.
            if used_read_aloud and last_read_text:
                self.last_tts_quality = "narrate"
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": last_read_text[:200]})
                return last_read_text
            try:
                msg = self._chat(messages, use_tools=True)
            except requests.RequestException as exc:
                log.error("Local LLM tool follow-up failed: %s", exc)
                # Fall back to last tool result if any
                last_tool = next(
                    (m["content"] for m in reversed(messages) if m.get("role") == "tool"),
                    "",
                )
                return last_tool or "The tool ran, but I lost the follow-up reply."

        reply = (msg.get("content") or "").strip()
        if not reply:
            # Some models return empty content after tools; surface last tool output
            for m in reversed(messages):
                if m.get("role") == "tool" and m.get("content"):
                    reply = str(m["content"])
                    break
        if not reply:
            reply = "I'm not sure how to help with that."

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})
        return reply
