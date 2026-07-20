"""Jan LLM client — Windows Local API with server-side MCP via /v1/orchestrations.

Pi responsibilities: wake / STT / TTS / room tools.
Windows Jan responsibilities: web search (Exa/fetch), reference research, image gen (stability-studio).
"""
from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

log = logging.getLogger("studio_edge.brain")


class JanBrain:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        system_prompt: str = "",
        timeout_s: int = 180,
        history_turns: int = 6,
        connect_timeout_s: float = 4.0,
        host_header: str = "",
        *,
        # server = Jan executes MCP on Windows (/v1/orchestrations)
        # chat = raw llama.cpp completions (no MCP)
        api_mode: str = "server",
        assistant_id: str = "",
        max_tokens: int = 280,
        cfg: dict | None = None,
        # Deprecated kwargs kept for call-site compatibility
        tools_enabled: bool = True,
        max_tool_rounds: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt.strip()
        self.timeout_s = timeout_s
        self.connect_timeout_s = connect_timeout_s
        self.host_header = host_header.strip()
        self.history: deque[dict[str, str]] = deque(maxlen=history_turns * 2)
        self.disable_thinking = True
        self.max_tokens = max_tokens
        self.api_mode = (api_mode or "server").strip().lower()
        self.assistant_id = (assistant_id or "").strip()
        self.cfg = cfg or {}
        # Unused; kept so older configs don't break
        self.tools_enabled = tools_enabled
        self.max_tool_rounds = max_tool_rounds

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self.host_header:
            h["Host"] = self.host_header
        return h

    def _root(self) -> str:
        """http://host:1337/v1 -> http://host:1337"""
        parsed = urlparse(self.base_url)
        path = parsed.path.rstrip("/")
        if path.endswith("/v1"):
            path = path[: -len("/v1")] or ""
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")

    def _endpoint(self, *, use_mcp: bool) -> str:
        root = self._root()
        if use_mcp and self.api_mode in {"server", "orchestrations", "mcp"}:
            return f"{root}/v1/orchestrations"
        return f"{self.base_url}/chat/completions"

    def _messages(self, user_text: str) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(self.history)
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def _payload(self, messages: list[dict[str, Any]], *, temperature: float) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "max_tokens": self.max_tokens,
        }
        if self.disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        if self.assistant_id:
            payload["assistant_id"] = self.assistant_id
        return payload

    @staticmethod
    def _message_text(msg: dict[str, Any]) -> str:
        content = (msg.get("content") or "").strip()
        if content:
            return content
        reason = (msg.get("reasoning_content") or "").strip()
        if reason:
            lines = [ln.strip() for ln in reason.splitlines() if ln.strip()]
            return lines[-1][:280] if lines else ""
        return ""

    def _chat(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float,
        use_mcp: bool,
    ) -> dict[str, Any]:
        url = self._endpoint(use_mcp=use_mcp)
        payload = self._payload(messages, temperature=temperature)
        log.info("Jan POST %s (mcp=%s)", url, use_mcp)
        r = requests.post(
            url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=(self.connect_timeout_s, self.timeout_s),
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]

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

    def ask(self, user_text: str, *, force_tool: str | None = None) -> str:
        """Spoken studio turn. MCP runs on Windows when api_mode=server.

        force_tool is ignored (kept for call-site compatibility) — Jan's MCP
        catalog on Windows decides which tools to call.
        """
        del force_tool  # Windows MCP owns tool selection
        messages = self._messages(user_text)
        try:
            msg = self._chat(messages, temperature=0.7, use_mcp=True)
            reply = self._message_text(msg)
            if not reply:
                return "Nari answered, but I couldn't hear the words."
        except requests.RequestException as exc:
            log.error("Studio brain request failed: %s", exc)
            # Fallback: raw chat if orchestrations is unavailable
            try:
                msg = self._chat(messages, temperature=0.7, use_mcp=False)
                reply = self._message_text(msg)
                if reply:
                    log.warning("Fell back to chat/completions (no MCP).")
                    self.history.append({"role": "user", "content": user_text})
                    self.history.append({"role": "assistant", "content": reply})
                    return reply
            except requests.RequestException:
                pass
            return "I couldn't reach Nari on the 8600G. Is Ollama running there?"
        except (KeyError, IndexError, ValueError) as exc:
            log.error("Unexpected studio brain response: %s", exc)
            return "I got a confusing answer from Nari."

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def instruct(self, directive: str, *, allow_chat_fallback: bool = False) -> str:
        """One-off instruction (generation / research) using Windows MCP.

        By default does NOT fall back to raw chat/completions — that path has no MCP
        and the model will invent 'I'll generate an image' without doing it.
        """
        messages: list[dict[str, Any]] = (
            [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        ) + [{"role": "user", "content": directive}]
        try:
            msg = self._chat(messages, temperature=0.4, use_mcp=True)
            return self._message_text(msg)
        except Exception as exc:  # noqa: BLE001
            log.error("Jan instruct failed: %s", exc)
            if not allow_chat_fallback:
                return ""
            try:
                msg = self._chat(messages, temperature=0.4, use_mcp=False)
                log.warning("Jan instruct used chat fallback (no MCP) — reply may be unreliable.")
                return self._message_text(msg)
            except Exception as exc2:  # noqa: BLE001
                log.error("Jan instruct fallback failed: %s", exc2)
                return ""
