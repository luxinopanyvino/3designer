"""Process-wide singletons shared by the routers."""

from app.config import settings
from app.services.jobs import JobManager
from app.services.session_store import SessionStore

store = SessionStore(settings.data_dir)
jobs = JobManager()


def version_urls(session_id: str, version: int) -> dict[str, str]:
    base = f"/api/sessions/{session_id}/versions/{version}"
    return {"model_url": f"{base}/model.glb", "code_url": f"{base}/code.py"}
