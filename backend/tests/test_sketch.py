import asyncio
import json

import cv2
import ezdxf
import numpy as np
import pytest

from app.services.dimensions import parse_target_size_mm
from app.services.llm import LLMService
from app.services.sketch import SketchError, _vectorize, generate_sketch


def _plate_png() -> bytes:
    """White canvas, 200x120 black plate with a 40x40 white hole."""
    canvas = np.full((300, 400), 255, dtype=np.uint8)
    cv2.rectangle(canvas, (100, 90), (300, 210), 0, thickness=-1)
    cv2.rectangle(canvas, (180, 130), (220, 170), 255, thickness=-1)
    ok, buf = cv2.imencode(".png", canvas)
    assert ok
    return buf.tobytes()


async def _noop_emit(event, data):
    pass


def test_parse_dimension_cases():
    assert parse_target_size_mm("altura 120 mm") == (120.0, "height")
    assert parse_target_size_mm("12,5 cm") == (125.0, None)
    assert parse_target_size_mm("ancho de 60 mm") == (60.0, "width")
    assert parse_target_size_mm("hazlo bonito") is None
    assert parse_target_size_mm("") is None


def test_vectorize_outer_and_hole():
    contours = _vectorize(_plate_png(), 0.0005, 0.005)
    outers = [c for c in contours if not c.hole]
    holes = [c for c in contours if c.hole]
    assert len(outers) == 1
    assert len(holes) == 1


def test_vectorize_blank_image_raises():
    blank = np.full((100, 100), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", blank)
    assert ok
    with pytest.raises(SketchError):
        _vectorize(buf.tobytes(), 0.0005, 0.005)


def test_generate_sketch_scales_from_prompt(tmp_path):
    info = asyncio.run(
        generate_sketch(
            image_bytes=_plate_png(),
            prompt="ancho 50 mm",
            target_size_mm=None,
            out_dir=tmp_path,
            emit=_noop_emit,
        )
    )
    assert info.dimensions_mm["x"] == pytest.approx(50.0, rel=0.02)
    assert info.dimensions_mm["y"] == pytest.approx(30.0, rel=0.05)  # 120/200 aspect
    assert info.dimensions_mm["z"] == 0.0
    assert info.volume_mm3 == 0.0

    doc = ezdxf.readfile(tmp_path / "model.dxf")
    polylines = list(doc.modelspace().query("LWPOLYLINE"))
    assert len(polylines) == 2
    assert doc.header["$INSUNITS"] == 4  # millimeters

    svg = (tmp_path / "preview.svg").read_text(encoding="utf-8")
    assert "<path" in svg and "evenodd" in svg


def test_generate_sketch_explicit_size_wins(tmp_path):
    info = asyncio.run(
        generate_sketch(
            image_bytes=_plate_png(),
            prompt="ancho 50 mm",
            target_size_mm=80.0,
            out_dir=tmp_path,
            emit=_noop_emit,
        )
    )
    assert info.dimensions_mm["x"] == pytest.approx(80.0, rel=0.02)


def test_llm_cleanup_replaces_contours(tmp_path, monkeypatch):
    called = {}

    async def fake_analyze(self, image_bytes, contours_json, prompt):
        called["prompt"] = prompt
        return json.dumps(
            {"contours": [{"points": [[0, 0], [40, 0], [40, 40], [0, 40]], "hole": False}]}
        )

    monkeypatch.setattr(LLMService, "analyze_sketch", fake_analyze)

    info = asyncio.run(
        generate_sketch(
            image_bytes=_plate_png(),
            prompt="solo el contorno exterior, ancho 40 mm",
            target_size_mm=None,
            out_dir=tmp_path,
            emit=_noop_emit,
        )
    )
    assert called["prompt"] == "solo el contorno exterior, ancho 40 mm"
    assert info.dimensions_mm["x"] == pytest.approx(40.0)
    assert info.warnings == []

    doc = ezdxf.readfile(tmp_path / "model.dxf")
    assert len(list(doc.modelspace().query("LWPOLYLINE"))) == 1


def test_llm_cleanup_failure_falls_back(tmp_path, monkeypatch):
    async def bad_analyze(self, image_bytes, contours_json, prompt):
        return "no json at all"

    monkeypatch.setattr(LLMService, "analyze_sketch", bad_analyze)

    info = asyncio.run(
        generate_sketch(
            image_bytes=_plate_png(),
            prompt="simplifica, ancho 50 mm",
            target_size_mm=None,
            out_dir=tmp_path,
            emit=_noop_emit,
        )
    )
    assert any("limpieza" in w.lower() for w in info.warnings)
    assert info.dimensions_mm["x"] == pytest.approx(50.0, rel=0.02)

    doc = ezdxf.readfile(tmp_path / "model.dxf")
    assert len(list(doc.modelspace().query("LWPOLYLINE"))) == 2  # CV contours kept
