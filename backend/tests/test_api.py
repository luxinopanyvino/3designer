import io

from tests.conftest import PNG_1PX, _sse_events


def _post_organic(client, sid, content="", target_size_mm=None):
    data = {"content": content, "mode": "organic"}
    if target_size_mm is not None:
        data["target_size_mm"] = target_size_mm
    return client.post(
        f"/api/sessions/{sid}/messages",
        data=data,
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "stl" in body["export_formats"]
    assert "dxf" in body["export_formats"]
    assert "step" not in body["export_formats"]


def test_session_lifecycle(client, fake_organic_service):
    sid = client.post("/api/sessions").json()["id"]

    r = _post_organic(client, sid, content="una figura", target_size_mm="50")
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    with client.stream("GET", f"/api/sessions/{sid}/events", params={"job_id": job_id}) as s:
        events = _sse_events(s)
    names = [n for n, _ in events]
    assert names[-1] == "completed"
    completed = events[-1][1]
    assert completed["version"] == 1
    assert completed["source"] == "organic"
    assert completed["model_url"].endswith("/versions/1/model.glb")
    assert completed["preview_url"] is None

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
    r = client.post("/api/sessions/nope/messages", data={"content": "x", "mode": "organic"})
    assert r.status_code == 404


def test_invalid_mode_rejected(client):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "una caja", "mode": "cad"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert r.status_code == 422


def test_missing_mode_rejected(client):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "una caja"},
        files={"image": ("ref.png", io.BytesIO(PNG_1PX), "image/png")},
    )
    assert r.status_code == 422


def test_image_required_in_both_modes(client):
    sid = client.post("/api/sessions").json()["id"]
    for mode in ("organic", "sketch"):
        r = client.post(f"/api/sessions/{sid}/messages", data={"content": "x", "mode": mode})
        assert r.status_code == 422
