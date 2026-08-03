import io

import trimesh

from app.services import organic
from tests.conftest import PNG_1PX, _sse_events


def test_image_upload_creates_message_with_url(client, monkeypatch):
    captured = {}

    async def spying_request(image_bytes: bytes) -> bytes:
        captured["image_bytes"] = image_bytes
        return trimesh.creation.icosphere(subdivisions=2, radius=1.0).export(file_type="stl")

    monkeypatch.setattr(organic, "request_organic_mesh", spying_request)

    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "una figura de 30 mm", "mode": "organic"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    with client.stream("GET", f"/api/sessions/{sid}/events", params={"job_id": job_id}) as s:
        events = _sse_events(s)
    assert events[-1][0] == "completed"
    assert captured["image_bytes"] == PNG_1PX

    session = client.get(f"/api/sessions/{sid}").json()
    user_msg = session["messages"][0]
    assert user_msg["image_url"] is not None

    img = client.get(user_msg["image_url"])
    assert img.status_code == 200 and img.content == PNG_1PX


def test_image_only_message_allowed(client, fake_organic_service):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"mode": "organic"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert r.status_code == 202


def test_text_without_image_rejected(client):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages", data={"content": "solo texto", "mode": "organic"}
    )
    assert r.status_code == 422


def test_unsupported_image_type_rejected(client):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "x", "mode": "organic"},
        files={"image": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r.status_code == 422
