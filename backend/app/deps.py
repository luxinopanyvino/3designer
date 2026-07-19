"""Process-wide singletons shared by the routers."""

from app.config import settings
from app.services.jobs import JobManager
from app.services.session_store import SessionStore

store = SessionStore(settings.data_dir)
jobs = JobManager()


def version_urls(session_id: str, version: int, source: str = "cad") -> dict[str, str | None]:
    base = f"/api/sessions/{session_id}/versions/{version}"
    if source == "sketch":
        return {"model_url": None, "preview_url": f"{base}/preview.svg"}
    return {"model_url": f"{base}/model.glb", "preview_url": None}
