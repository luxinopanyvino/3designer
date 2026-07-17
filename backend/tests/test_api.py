import json

import pytest
import trimesh
from fastapi.testclient import TestClient

from app import deps
from app.main import app
from app.routers import sessions as sessions_router
from app.services.generation import GenerationFailed, GenerationResult
from app.services.mesh_service import MeshInfo
from app.services.session_store import SessionStore


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
def fake_generation(monkeypatch):
    """Replace the LLM+CAD pipeline with a stub that writes real (tiny) files."""

    async def fake_generate_model(*, out_dir, emit, **kwargs):
        out_dir.mkdir(parents=True, exist_ok=True)
        mesh = trimesh.creation.box(extents=(30, 20, 10))
        stl, step, glb = out_dir / "model.stl", out_dir / "model.step", out_dir / "model.glb"
        mesh.export(stl)
        step.write_text("fake step", encoding="utf-8")
        glb.write_bytes(mesh.export(file_type="glb"))
        (out_dir / "code.py").write_text("result = None", encoding="utf-8")
        await emit("status", {"stage": "llm_generating", "attempt": 1})
        await emit("code_delta", {"text": "result = None"})
        await emit("status", {"stage": "executing", "attempt": 1})
        return GenerationResult(
            code="result = None",
            mesh_info=MeshInfo(
                dimensions_mm={"x": 30.0, "y": 20.0, "z": 10.0},
                volume_mm3=6000.0,
                watertight=True,
                warnings=[],
            ),
            stl_path=stl,
            step_path=step,
            glb_path=glb,
        )

    monkeypatch.setattr(sessions_router, "generate_model", fake_generate_model)


def _sse_events(response):
    events = []
    current = None
    for line in response.iter_lines():
        if line.startswith("event:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and current:
            events.append((current, json.loads(line.split(":", 1)[1])))
    return events


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "stl" in body["export_formats"]


def test_session_lifecycle(client, fake_generation):
    sid = client.post("/api/sessions").json()["id"]

    r = client.post(f"/api/sessions/{sid}/messages", json={"content": "a box"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    with client.stream("GET", f"/api/sessions/{sid}/events", params={"job_id": job_id}) as s:
        events = _sse_events(s)
    names = [n for n, _ in events]
    assert names[-1] == "completed"
    completed = events[-1][1]
    assert completed["version"] == 1
    assert completed["dimensions_mm"]["x"] == 30.0
    assert completed["model_url"].endswith("/versions/1/model.glb")

    session = client.get(f"/api/sessions/{sid}").json()
    assert [m["role"] for m in session["messages"]] == ["user", "assistant"]
    assert len(session["versions"]) == 1

    glb = client.get(f"/api/sessions/{sid}/versions/1/model.glb")
    assert glb.status_code == 200 and len(glb.content) > 0

    stl = client.get(f"/api/sessions/{sid}/export", params={"format": "stl"})
    assert stl.status_code == 200
    assert "model_v1.stl" in stl.headers["content-disposition"]


def test_unknown_session_404(client):
    assert client.get("/api/sessions/nope").status_code == 404
    assert client.post("/api/sessions/nope/messages", json={"content": "x"}).status_code == 404


def test_generation_failure_reported(client, monkeypatch):
    async def failing_generate_model(*, out_dir, emit, **kwargs):
        await emit("status", {"stage": "llm_generating", "attempt": 1})
        raise GenerationFailed("Could not build", attempts=3, last_error="boom")

    monkeypatch.setattr(sessions_router, "generate_model", failing_generate_model)

    sid = client.post("/api/sessions").json()["id"]
    job_id = client.post(f"/api/sessions/{sid}/messages", json={"content": "impossible"}).json()["job_id"]
    with client.stream("GET", f"/api/sessions/{sid}/events", params={"job_id": job_id}) as s:
        events = _sse_events(s)
    assert events[-1][0] == "error"
    assert events[-1][1]["attempts"] == 3

    session = client.get(f"/api/sessions/{sid}").json()
    assert session["messages"][-1]["error"] is True
    assert session["versions"] == []
