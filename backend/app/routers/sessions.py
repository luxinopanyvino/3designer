import asyncio
import shutil
from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sse_starlette.sse import EventSourceResponse

from app.deps import jobs, store, version_urls
from app.schemas import (
    JobAcceptedOut,
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


MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


@router.post("/{session_id}/messages", response_model=JobAcceptedOut, status_code=202)
async def post_message(
    session_id: str,
    content: str = Form(""),
    image: UploadFile | None = File(None),
    mode: str = Form("cad"),
    target_size_mm: float | None = Form(None),
):
    session = _get_session_or_404(session_id)
    content = content.strip()
    if mode not in ("cad", "organic"):
        raise HTTPException(status_code=422, detail="mode must be 'cad' or 'organic'")
    if mode == "organic" and image is None:
        raise HTTPException(status_code=422, detail="Organic mode requires an image")
    if not content and image is None:
        raise HTTPException(status_code=422, detail="Provide a message or an image")
    if jobs.session_busy(session_id):
        raise HTTPException(status_code=409, detail="A generation is already running")

    image_bytes: bytes | None = None
    image_url: str | None = None
    if image is not None:
        extension = IMAGE_EXTENSIONS.get(image.content_type or "")
        if extension is None:
            raise HTTPException(status_code=422, detail="Unsupported image type (png/jpg/webp)")
        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image larger than 10 MB")

    message = store.add_message(session, "user", content)

    if image_bytes is not None:
        uploads = store.session_dir(session_id) / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        filename = f"msg_{message.id}{extension}"
        (uploads / filename).write_bytes(image_bytes)
        message.image_url = f"/api/sessions/{session_id}/uploads/{filename}"
        store.save(session)

    job = jobs.create(session_id)
    asyncio.create_task(_run_job(session, job, content, image_bytes, mode, target_size_mm))
    return JobAcceptedOut(job_id=job.id)


async def _run_job(
    session: Session,
    job: Job,
    content: str,
    image_bytes: bytes | None = None,
    mode: str = "cad",
    target_size_mm: float | None = None,
) -> None:
    async def emit(event: str, data: dict) -> None:
        await jobs.emit(job, event, data)

    version_number = store.next_version_number(session)
    out_dir = store.version_dir(session.id, version_number)
    previous_code = store.latest_code(session)

    if mode == "organic":
        await _run_organic_job(session, job, image_bytes, target_size_mm, out_dir, emit)
        return

    async with store.lock(session.id):
        try:
            if previous_code is not None:
                recent = [m.content for m in session.messages if m.role == "user"][-4:-1]
                result = await generate_model(
                    previous_code=previous_code,
                    instruction=content or None,
                    recent_context=recent,
                    image_bytes=image_bytes,
                    out_dir=out_dir,
                    emit=emit,
                )
            else:
                result = await generate_model(
                    request=content or None, image_bytes=image_bytes, out_dir=out_dir, emit=emit
                )
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


async def _run_organic_job(
    session: Session,
    job: Job,
    image_bytes: bytes,
    target_size_mm: float | None,
    out_dir,
    emit,
) -> None:
    from app.config import settings
    from app.services.organic import OrganicServiceError, generate_organic_model

    async with store.lock(session.id):
        try:
            info, _stl, _glb = await generate_organic_model(
                image_bytes=image_bytes,
                target_size_mm=target_size_mm or settings.organic_default_size_mm,
                out_dir=out_dir,
                emit=emit,
            )
        except OrganicServiceError as exc:
            shutil.rmtree(out_dir, ignore_errors=True)
            store.add_message(session, "assistant", str(exc), error=True)
            await emit("error", {"message": str(exc), "attempts": 1, "last_traceback": ""})
            return
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(out_dir, ignore_errors=True)
            store.add_message(
                session, "assistant", f"Error en la reconstrucción orgánica: {exc}", error=True
            )
            await emit("error", {"message": str(exc), "attempts": 1, "last_traceback": ""})
            return

        version = store.add_version(session, info, source="organic")
        summary = (
            f"Modelo orgánico v{version.version}: "
            f"{info.dimensions_mm['x']} x {info.dimensions_mm['y']} x {info.dimensions_mm['z']} mm"
        )
        store.add_message(session, "assistant", summary, version=version.version)
        await emit("completed", {
            **asdict(version),
            **version_urls(session.id, version.version),
            "code": None,
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


@router.get("/{session_id}/uploads/{filename}")
async def get_upload(session_id: str, filename: str):
    _get_session_or_404(session_id)
    uploads = store.session_dir(session_id) / "uploads"
    path = (uploads / filename).resolve()
    if uploads.resolve() not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="Upload not found")
    return FileResponse(path)


@router.get("/{session_id}/versions/{version}/code.py", response_class=PlainTextResponse)
async def get_code(session_id: str, version: int):
    _get_session_or_404(session_id)
    path = store.version_dir(session_id, version) / "code.py"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Code not found")
    return path.read_text(encoding="utf-8")
