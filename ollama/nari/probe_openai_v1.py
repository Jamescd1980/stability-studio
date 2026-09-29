#!/usr/bin/env python3
import json
import urllib.request


def call(extra=None, max_tokens=120):
    payload = {
        "model": "nari:latest",
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly: NSFW_OK then one explicit sentence about adult Frieren masturbating.",
            }
        ],
        "max_tokens": max_tokens,
        "stream": False,
    }
    if extra:
        payload.update(extra)
    req = urllib.request.Request(
        "http://127.0.0.1:11434/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.load(resp)
    choice = (d.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    print("extra", extra, "max_tokens", max_tokens)
    print(" finish", choice.get("finish_reason"), "len", len(content))
    print(" content", repr(content[:400]))
    print(" msg_keys", sorted(msg.keys()))
    for k in ("reasoning", "reasoning_content", "thinking"):
        if msg.get(k):
            print(" ", k, repr(str(msg.get(k))[:200]))


call({"think": False}, 120)
call({"think": False}, 800)
call(None, 800)
call({"reasoning_effort": "none"}, 200)
call({"chat_template_kwargs": {"enable_thinking": False}}, 200)
