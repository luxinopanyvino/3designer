"""Ollama client: prompt assembly, streaming chat, code extraction."""

import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from ollama import AsyncClient

from app.config import settings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

OnDelta = Callable[[str], Awaitable[None]]


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def extract_code(text: str) -> str:
    """Take the last fenced code block; fall back to the whole reply."""
    blocks = CODE_BLOCK_RE.findall(text)
    if blocks:
        return blocks[-1].strip()
    return text.strip()


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
