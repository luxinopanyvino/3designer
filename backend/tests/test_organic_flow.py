import io

import pytest
import trimesh

from app.services import organic
from app.services.organic import OrganicServiceError, repair_and_normalize
from tests.conftest import PNG_1PX, _sse_events


def _dirty_stl() -> bytes:
    """Two components (big + small), unnormalized scale, floating above origin."""
    big = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    big.apply_translation([5, 3, 7])
    small = trimesh.creation.box(extents=(0.1, 0.1, 0.1))
    small.apply_translation([-4, 0, 2])
    return trimesh.util.concatenate([big, small]).export(file_type="stl")


def test_repair_keeps_largest_component_scales_and_grounds():
    mesh = repair_and_normalize(_dirty_stl(), target_size_mm=80.0)
    extents = mesh.extents
    assert extents.max() == pytest.approx(80.0, rel=0.01)
    bounds = mesh.bounds
    assert bounds[0][2] == pytest.approx(0.0, abs=1e-6)  # sits on the bed
    center_x = (bounds[0][0] + bounds[1][0]) / 2
    assert center_x == pytest.approx(0.0, abs=1e-6)
    assert mesh.is_watertight  # the sphere survived; the noise cube did not


def test_repair_rejects_empty():
    empty = trimesh.creation.box().export(file_type="stl")[:84]  # header only
    with pytest.raises((OrganicServiceError, Exception)):
        repair_and_normalize(empty, 80.0)


def test_organic_job_creates_version(client, fake_organic_service):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "una figura", "mode": "organic", "target_size_mm": "50"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert r.status_code == 202
    with client.stream(
        "GET", f"/api/sessions/{sid}/events", params={"job_id": r.json()["job_id"]}
    ) as s:
        events = _sse_events(s)

    names = [n for n, _ in events]
    assert "status" in names and events[-1][0] == "completed"
    completed = events[-1][1]
    assert completed["source"] == "organic"
    assert "code" not in completed
    assert max(completed["dimensions_mm"].values()) == pytest.approx(50.0, rel=0.01)

    glb = client.get(f"/api/sessions/{sid}/versions/1/model.glb")
    assert glb.status_code == 200

    stl = client.get(f"/api/sessions/{sid}/export", params={"format": "stl"})
    assert stl.status_code == 200
    step = client.get(f"/api/sessions/{sid}/export", params={"format": "step"})
    assert step.status_code == 422  # STEP no longer exists as a format


def test_organic_size_from_prompt(client, fake_organic_service, monkeypatch):
    captured = {}
    original = organic.generate_organic_model

    async def spying_generate(**kwargs):
        captured["target_size_mm"] = kwargs["target_size_mm"]
        return await original(**kwargs)

    monkeypatch.setattr(organic, "generate_organic_model", spying_generate)

    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "una figura de altura 120 mm", "mode": "organic"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    with client.stream(
        "GET", f"/api/sessions/{sid}/events", params={"job_id": r.json()["job_id"]}
    ) as s:
        events = _sse_events(s)
    assert events[-1][0] == "completed"
    assert captured["target_size_mm"] == 120.0


def test_organic_requires_image(client):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages", data={"content": "una figura", "mode": "organic"}
    )
    assert r.status_code == 422


def test_organic_service_down_reports_error(client, monkeypatch):
    async def failing_request(image_bytes: bytes) -> bytes:
        raise OrganicServiceError("El servicio de reconstrucción orgánica no responde")

    monkeypatch.setattr(organic, "request_organic_mesh", failing_request)

    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"mode": "organic"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    with client.stream(
        "GET", f"/api/sessions/{sid}/events", params={"job_id": r.json()["job_id"]}
    ) as s:
        events = _sse_events(s)
    assert events[-1][0] == "error"
    assert "no responde" in events[-1][1]["message"]
