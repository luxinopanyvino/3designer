import asyncio
import shutil
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from app.deps import jobs, store, version_urls
from app.schemas import (
    JobAcceptedOut,
    MessageIn,
    SessionCreatedOut,
    SessionOut,
)
from app.services.generation import GenerationFailed, generate_model
from app.services.jobs import Job
from app.services.session_store import Session

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_session_or_404(session_id: str) -> Session:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=SessionCreatedOut, status_code=201)
async def create_session():
    session = store.create()
    return SessionCreatedOut(id=session.id, created_at=session.created_at)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: str):
    session = _get_session_or_404(session_id)
    return SessionOut(
        id=session.id,
        created_at=session.created_at,
        messages=[asdict(m) for m in session.messages],
        versions=[
            {**asdict(v), **version_urls(session.id, v.version)} for v in session.versions
        ],
    )


@router.post("/{session_id}/messages", response_model=JobAcceptedOut, status_code=202)
async def post_message(session_id: str, body: MessageIn):
    session = _get_session_or_404(session_id)
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content is empty")
    if jobs.session_busy(session_id):
        raise HTTPException(status_code=409, detail="A generation is already running")

    store.add_message(session, "user", content)
    job = jobs.create(session_id)
    asyncio.create_task(_run_job(session, job, content))
    return JobAcceptedOut(job_id=job.id)


async def _run_job(session: Session, job: Job, content: str) -> None:
    async def emit(event: str, data: dict) -> None:
        await jobs.emit(job, event, data)

    version_number = store.next_version_number(session)
    out_dir = store.version_dir(session.id, version_number)
    previous_code = store.latest_code(session)

    async with store.lock(session.id):
        try:
            if previous_code is not None:
                recent = [m.content for m in session.messages if m.role == "user"][-4:-1]
                result = await generate_model(
                    previous_code=previous_code,
                    instruction=content,
                    recent_context=recent,
                    out_dir=out_dir,
                    emit=emit,
                )
            else:
                result = await generate_model(request=content, out_dir=out_dir, emit=emit)
        except GenerationFailed as exc:
            shutil.rmtree(out_dir, ignore_errors=True)
            store.add_message(
                session,
                "assistant",
                f"No pude construir un modelo válido tras {exc.attempts} intentos. "
                f"Último error:\n{exc.last_error}",
                error=True,
            )
            await emit("error", {
                "message": str(exc),
                "attempts": exc.attempts,
                "last_traceback": exc.last_error,
            })
            return
        except Exception as exc:  # noqa: BLE001 - infra errors (Ollama down, etc.)
            shutil.rmtree(out_dir, ignore_errors=True)
            store.add_message(
                session, "assistant", f"Error interno de generación: {exc}", error=True
            )
            await emit("error", {"message": str(exc), "attempts": 0, "last_traceback": ""})
            return

        version = store.add_version(session, result.mesh_info)
        info = result.mesh_info
        summary = (
            f"Modelo v{version.version}: "
            f"{info.dimensions_mm['x']} x {info.dimensions_mm['y']} x {info.dimensions_mm['z']} mm"
        )
        store.add_message(session, "assistant", summary, version=version.version)
        await emit("completed", {
            **asdict(version),
            **version_urls(session.id, version.version),
            "code": result.code,
        })


@router.get("/{session_id}/events")
async def stream_events(session_id: str, job_id: str):
    _get_session_or_404(session_id)
    job = jobs.get(job_id)
    if job is None or job.session_id != session_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return EventSourceResponse(jobs.stream(job))


@router.get("/{session_id}/versions/{version}/model.glb")
async def get_model_glb(session_id: str, version: int):
    _get_session_or_404(session_id)
    path = store.version_dir(session_id, version) / "model.glb"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Model not found")
    return FileResponse(path, media_type="model/gltf-binary")


@router.get("/{session_id}/versions/{version}/code.py", response_class=PlainTextResponse)
async def get_code(session_id: str, version: int):
    _get_session_or_404(session_id)
    path = store.version_dir(session_id, version) / "code.py"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Code not found")
    return path.read_text(encoding="utf-8")
