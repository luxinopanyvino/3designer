"""API flow for sketch mode — needs no external services (pure CV path)."""

import io

import cv2
import numpy as np

from tests.conftest import _sse_events


def _plate_png() -> bytes:
    canvas = np.full((300, 400), 255, dtype=np.uint8)
    cv2.rectangle(canvas, (100, 90), (300, 210), 0, thickness=-1)
    ok, buf = cv2.imencode(".png", canvas)
    assert ok
    return buf.tobytes()


def test_sketch_job_creates_version(client):
    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"content": "ancho 60 mm", "mode": "sketch"},
        files={"image": ("plate.png", io.BytesIO(_plate_png()), "image/png")},
    )
    assert r.status_code == 202
    with client.stream(
        "GET", f"/api/sessions/{sid}/events", params={"job_id": r.json()["job_id"]}
    ) as s:
        events = _sse_events(s)

    names = [n for n, _ in events]
    assert "status" in names and events[-1][0] == "completed"
    completed = events[-1][1]
    assert completed["source"] == "sketch"
    assert completed["model_url"] is None
    assert completed["preview_url"].endswith("/versions/1/preview.svg")
    assert completed["dimensions_mm"]["x"] == 60.0
    assert completed["dimensions_mm"]["z"] == 0.0

    svg = client.get(f"/api/sessions/{sid}/versions/1/preview.svg")
    assert svg.status_code == 200
    assert b"<path" in svg.content

    dxf = client.get(f"/api/sessions/{sid}/export", params={"format": "dxf"})
    assert dxf.status_code == 200
    assert "model_v1.dxf" in dxf.headers["content-disposition"]

    svg_export = client.get(f"/api/sessions/{sid}/export", params={"format": "svg"})
    assert svg_export.status_code == 200

    stl = client.get(f"/api/sessions/{sid}/export", params={"format": "stl"})
    assert stl.status_code == 404  # no mesh for a 2D version

    step = client.get(f"/api/sessions/{sid}/export", params={"format": "step"})
    assert step.status_code == 422


def test_sketch_no_contours_reports_error(client):
    blank = np.full((100, 100), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", blank)
    assert ok

    sid = client.post("/api/sessions").json()["id"]
    r = client.post(
        f"/api/sessions/{sid}/messages",
        data={"mode": "sketch"},
        files={"image": ("blank.png", io.BytesIO(buf.tobytes()), "image/png")},
    )
    with client.stream(
        "GET", f"/api/sessions/{sid}/events", params={"job_id": r.json()["job_id"]}
    ) as s:
        events = _sse_events(s)
    assert events[-1][0] == "error"
    assert "contorno" in events[-1][1]["message"]

    session = client.get(f"/api/sessions/{sid}").json()
    assert session["versions"] == []
    assert session["messages"][-1]["error"] is True
