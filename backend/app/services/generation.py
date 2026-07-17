"""Orchestrator: LLM -> safety check -> sandboxed execution -> mesh validation,
with a self-correction loop that feeds errors back to the LLM.

Independent of the HTTP layer: progress is reported through an async `emit`
callback so both the CLI harness and the SSE endpoint can drive it.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.services import llm as llm_mod
from app.services.cad_executor import execute_cad_code
from app.services.code_safety import check_code
from app.services.llm import LLMService, extract_code
from app.services.mesh_service import (
    DegenerateMeshError,
    MeshInfo,
    analyze_stl,
    convert_stl_to_glb,
)

Emit = Callable[[str, dict], Awaitable[None]]


@dataclass
class GenerationResult:
    code: str
    mesh_info: MeshInfo
    stl_path: Path
    step_path: Path
    glb_path: Path


class GenerationFailed(Exception):
    def __init__(self, message: str, attempts: int, last_error: str):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


IMAGE_BRIEF_TEMPLATE = (
    "\n\nDesign brief extracted from the user's reference image (JSON):\n{brief}\n"
    "The user's text gives the real dimensions; scale the estimated proportions "
    "from the brief to match them. If the user gave no dimensions, use the "
    "brief's estimates."
)

DEFAULT_IMAGE_REQUEST = "Reproduce the part shown in the reference image."


async def generate_model(
    *,
    request: str | None = None,
    previous_code: str | None = None,
    instruction: str | None = None,
    recent_context: list[str] | None = None,
    image_bytes: bytes | None = None,
    out_dir: Path,
    emit: Emit,
    llm: LLMService | None = None,
) -> GenerationResult:
    """First generation: pass `request`. Refinement: pass `previous_code` + `instruction`.
    An optional reference image is analyzed by the vision model and injected as a brief."""
    llm = llm or LLMService()
    out_dir.mkdir(parents=True, exist_ok=True)

    if image_bytes is not None:
        await emit("status", {"stage": "vision_analyzing", "attempt": 1})
        brief = await llm.analyze_image(image_bytes)
        await emit("vision_result", {"brief": brief})
        suffix = IMAGE_BRIEF_TEMPLATE.format(brief=brief)
        if previous_code is not None:
            instruction = (instruction or DEFAULT_IMAGE_REQUEST) + suffix
        else:
            request = (request or DEFAULT_IMAGE_REQUEST) + suffix

    if previous_code is not None and instruction is not None:
        messages = llm_mod.refine_messages(previous_code, instruction, recent_context or [])
    elif request is not None:
        messages = llm_mod.generate_messages(request)
    else:
        raise ValueError("Provide either `request` or (`previous_code` and `instruction`).")

    async def on_delta(token: str) -> None:
        await emit("code_delta", {"text": token})

    await emit("status", {"stage": "llm_generating", "attempt": 1})
    raw = await llm.chat_stream(messages, temperature=0.2, on_delta=on_delta)
    code = extract_code(raw)

    max_attempts = settings.max_repair_attempts
    error: str | None = None

    for attempt in range(1, max_attempts + 1):
        error = check_code(code)

        exec_result = None
        if error is None:
            await emit("status", {"stage": "executing", "attempt": attempt})
            exec_result = await asyncio.to_thread(
                execute_cad_code, code, out_dir, settings.exec_timeout_s
            )
            error = exec_result.error

        mesh_info = None
        if error is None:
            try:
                mesh_info = await asyncio.to_thread(
                    analyze_stl,
                    exec_result.stl_path,
                    settings.bed_size_mm,
                    settings.max_height_mm,
                )
            except DegenerateMeshError as exc:
                error = str(exc)

        if error is None:
            glb_path = out_dir / "model.glb"
            await asyncio.to_thread(convert_stl_to_glb, exec_result.stl_path, glb_path)
            return GenerationResult(
                code=code,
                mesh_info=mesh_info,
                stl_path=exec_result.stl_path,
                step_path=exec_result.step_path,
                glb_path=glb_path,
            )

        if attempt == max_attempts:
            break

        await emit("status", {"stage": "repairing", "attempt": attempt + 1})
        raw = await llm.chat_stream(
            llm_mod.repair_messages(code, error), temperature=0.4, on_delta=on_delta
        )
        code = extract_code(raw)

    raise GenerationFailed(
        f"Could not build a valid model after {max_attempts} attempts.",
        attempts=max_attempts,
        last_error=error or "unknown",
    )
