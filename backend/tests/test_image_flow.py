import io

import pytest

from app.services.llm import extract_json
from tests.test_api import _sse_events, client, fake_generation  # noqa: F401

PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01\x87\xa1N\xe8\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_extract_json_fenced():
    assert extract_json('Here:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_bare():
    assert extract_json('prose {"part_type": "washer", "n": 2} more prose') == {
        "part_type": "washer",
        "n": 2,
    }


def test_extract_json_invalid_returns_none():
    assert extract_json("no json here") is None


def test_image_upload_creates_message_with_url(client, fake_generation, monkeypatch):  # noqa: F811
    from app.routers import sessions as sessions_router

    captured = {}
    original = sessions_router.generate_model

    async def spying_generate_model(**kwargs):
        captured["image_bytes"] = kwargs.get("image_bytes")
        return await original(**kwargs)

    monkeypatch.setattr(sessions_router, "generate_model", spying_generate_model)

    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "una arandela de 30 mm"},
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


def test_image_only_message_allowed(client, fake_generation):  # noqa: F811
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert r.status_code == 202


def test_empty_message_rejected(client):  # noqa: F811
    sid = client.post("/api/sessions").json()["id"]
    assert client.post(f"/api/sessions/{sid}/messages", data={"content": "  "}).status_code == 422


def test_unsupported_image_type_rejected(client):  # noqa: F811
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "x"},
        files={"image": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r.status_code == 422
