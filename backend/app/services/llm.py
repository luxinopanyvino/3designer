"""Ollama client: prompt loading, streaming chat, JSON extraction."""

import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from ollama import AsyncClient

from app.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)

OnDelta = Callable[[str], Awaitable[None]]


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def extract_json(text: str) -> dict | None:
    """Pull a JSON object out of an LLM reply (fenced or bare); None if unparseable."""
    candidates = JSON_FENCE_RE.findall(text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


class LLMService:
    def __init__(self, host: str | None = None, model: str | None = None):
        self.client = AsyncClient(host=host or settings.ollama_host)
        self.model = model or settings.model_vision

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        on_delta: OnDelta | None = None,
    ) -> str:
        parts: list[str] = []
        stream = await self.client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={
                "temperature": temperature,
                "num_ctx": 8192,
                "num_predict": 2048,
            },
        )
        async for chunk in stream:
            token = chunk["message"]["content"]
            if not token:
                continue
            parts.append(token)
            if on_delta is not None:
                await on_delta(token)
        return "".join(parts)

    async def analyze_sketch(
        self, image_bytes: bytes, contours_json: str, prompt: str
    ) -> str:
        """Ask the vision model to clean up vectorized contours per the user's request.

        Returns the raw reply (a JSON string when the model behaved); the caller
        parses it with extract_json and falls back to the CV contours on failure.
        """
        messages = [
            {
                "role": "user",
                "content": load_prompt("sketch_refine").format(
                    contours=contours_json, instruction=prompt
                ),
                "images": [image_bytes],
            }
        ]
        # qwen3-vl thinks even with think=False (Ollama stopped honoring it),
        # and num_predict caps thinking+content together, so give it a large
        # budget and retry once if reasoning still swallowed the reply.
        options = {"temperature": 0.1, "num_predict": 8192}
        raw = ""
        for _ in range(2):
            try:
                response = await self.client.chat(
                    model=settings.model_vision, messages=messages, options=options, think=False
                )
            except Exception:
                response = await self.client.chat(
                    model=settings.model_vision, messages=messages, options=options
                )
            raw = response["message"]["content"]
            if raw.strip():
                break
        parsed = extract_json(raw)
        return json.dumps(parsed, ensure_ascii=False) if parsed else raw.strip()
