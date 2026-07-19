"""Ollama client: prompt assembly, streaming chat, code extraction."""

import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from ollama import AsyncClient

from app.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)

OnDelta = Callable[[str], Awaitable[None]]


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def extract_code(text: str) -> str:
    """Take the last fenced code block; fall back to the whole reply."""
    blocks = CODE_BLOCK_RE.findall(text)
    if blocks:
        return blocks[-1].strip()
    return text.strip()


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


def generate_messages(request: str) -> list[dict]:
    return [
        {"role": "system", "content": load_prompt("system_cadquery")},
        {"role": "user", "content": load_prompt("generate").format(request=request)},
    ]


def refine_messages(previous_code: str, instruction: str, recent_context: list[str]) -> list[dict]:
    context = "\n".join(f"- {m}" for m in recent_context) or "(none)"
    return [
        {"role": "system", "content": load_prompt("system_cadquery")},
        {
            "role": "user",
            "content": load_prompt("refine").format(
                previous_code=previous_code, instruction=instruction, context=context
            ),
        },
    ]


def repair_messages(code: str, error: str) -> list[dict]:
    return [
        {"role": "system", "content": load_prompt("system_cadquery")},
        {"role": "user", "content": load_prompt("repair").format(code=code, error=error)},
    ]


class LLMService:
    def __init__(self, host: str | None = None, model: str | None = None):
        self.client = AsyncClient(host=host or settings.ollama_host)
        self.model = model or settings.model_code

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

    async def analyze_image(self, image_bytes: bytes) -> str:
        """Describe a reference image as a structured design brief (JSON string).

        Runs the vision model (Ollama swaps models in VRAM sequentially).
        Falls back to the raw reply if the model didn't return valid JSON.
        """
        messages = [
            {
                "role": "user",
                "content": load_prompt("vision_analyze"),
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
