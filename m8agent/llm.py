from __future__ import annotations

import json
import os
from urllib import request
from urllib.error import HTTPError, URLError

from .db import SearchResult


SYSTEM_PROMPT = """You answer questions about the Dirtywave M8 using retrieved video transcript excerpts.
Use only the provided context. If the context is insufficient, say what is missing.
Answer practically, with M8 workflow steps when possible. Cite relevant sources as [1], [2], etc."""


def build_context(results: list[SearchResult]) -> str:
    blocks = []
    for idx, result in enumerate(results, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{idx}] {result.title}",
                    f"URL: {result.citation_url}",
                    f"Time: {result.timestamp}",
                    f"Language: {result.lang}",
                    f"Transcript: {result.text}",
                ]
            )
        )
    return "\n\n".join(blocks)


def answer_with_llm(question: str, results: list[SearchResult]) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("M8AGENT_MODEL") or os.environ.get("OPENAI_MODEL")
    if not api_key or not model:
        return None

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nContext:\n{build_context(results)}",
            },
        ],
        "temperature": 0.2,
    }

    req = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    return data["choices"][0]["message"]["content"].strip()
