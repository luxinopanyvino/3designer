"""Shared fixtures: fresh session store per test, stubbed organic service, SSE helper."""

import json

import pytest
import trimesh
from fastapi.testclient import TestClient

from app import deps
from app.main import app
from app.routers import sessions as sessions_router
from app.services import organic
from app.services.session_store import SessionStore

PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01\x87\xa1N\xe8\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    fresh_store = SessionStore(tmp_path)
    monkeypatch.setattr(deps, "store", fresh_store)
    monkeypatch.setattr(sessions_router, "store", fresh_store)
    import app.routers.export as export_router

    monkeypatch.setattr(export_router, "store", fresh_store)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fake_organic_service(monkeypatch):
    async def fake_request(image_bytes: bytes) -> bytes:
        return trimesh.creation.icosphere(subdivisions=2, radius=1.0).export(file_type="stl")

    monkeypatch.setattr(organic, "request_organic_mesh", fake_request)


def _sse_events(response):
    events = []
    current = None
    for line in response.iter_lines():
        if line.startswith("event:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and current:
            events.append((current, json.loads(line.split(":", 1)[1])))
    return events
