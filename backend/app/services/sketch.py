"""Image -> 2D DXF pipeline: OpenCV contour vectorization.

Fully deterministic: the prompt only supplies the real-world dimension, which
`dimensions.parse_target_size_mm` reads with a regex.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import cv2
import ezdxf
import numpy as np

from app.config import settings
from app.services.dimensions import parse_target_size_mm
from app.services.mesh_service import MeshInfo


class SketchError(Exception):
    """The sketch pipeline failed; message is user-facing."""


@dataclass
class Contour:
    points: list[tuple[float, float]]  # y-up, closed implicitly (last point != first)
    hole: bool


def _vectorize(image_bytes: bytes, min_area_frac: float, epsilon_frac: float) -> list[Contour]:
    data = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise SketchError("No se pudo decodificar la imagen.")
    height, width = img.shape

    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # The part must come out white. If the border (assumed background) is mostly
    # white, Otsu's polarity guessed wrong -> flip.
    border = np.concatenate([binary[0, :], binary[-1, :], binary[:, 0], binary[:, -1]])
    if border.mean() > 127:
        binary = cv2.bitwise_not(binary)

    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise SketchError("No se detectó ningún contorno en la imagen.")

    min_area = min_area_frac * width * height
    result: list[Contour] = []
    for contour, info in zip(contours, hierarchy[0]):
        if cv2.contourArea(contour) < min_area:
            continue
        epsilon = epsilon_frac * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) < 3:
            continue
        points = [(float(x), float(height - y)) for x, y in approx[:, 0, :]]  # y-up
        result.append(Contour(points=points, hole=bool(info[3] != -1)))

    if not any(not c.hole for c in result):
        raise SketchError("No se detectó ningún contorno en la imagen.")
    return result


def _bbox(contours: list[Contour]) -> tuple[float, float, float, float]:
    xs = [p[0] for c in contours for p in c.points]
    ys = [p[1] for c in contours for p in c.points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _scale_to_target(contours: list[Contour], value_mm: float, axis: str | None) -> list[Contour]:
    min_x, min_y, width, height = _bbox(contours)
    reference = height if axis == "height" else width
    if reference <= 0:
        raise SketchError("El contorno detectado es degenerado.")
    scale = value_mm / reference
    return [
        Contour(
            points=[((p[0] - min_x) * scale, (p[1] - min_y) * scale) for p in c.points],
            hole=c.hole,
        )
        for c in contours
    ]


def _write_dxf(contours: list[Contour], path: Path) -> None:
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # millimeters
    msp = doc.modelspace()
    for contour in contours:
        msp.add_lwpolyline(contour.points, close=True)
    doc.saveas(path)


def _write_svg(contours: list[Contour], width: float, height: float, path: Path) -> None:
    subpaths = []
    for contour in contours:
        cmds = " ".join(
            f"{'M' if i == 0 else 'L'} {x:.3f} {height - y:.3f}"  # SVG is y-down
            for i, (x, y) in enumerate(contour.points)
        )
        subpaths.append(cmds + " Z")
    stroke = 0.004 * max(width, height)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.3f} {height:.3f}">'
        f'<path fill-rule="evenodd" fill="#ddd" stroke="#111" stroke-width="{stroke:.3f}" '
        f'd="{" ".join(subpaths)}"/></svg>'
    )
    path.write_text(svg, encoding="utf-8")


async def generate_sketch(
    *,
    image_bytes: bytes,
    prompt: str,
    target_size_mm: float | None,
    out_dir: Path,
    emit,
) -> MeshInfo:
    await emit("status", {"stage": "vectorizing", "attempt": 1})
    contours = await asyncio.to_thread(
        _vectorize,
        image_bytes,
        settings.sketch_min_contour_area_frac,
        settings.sketch_simplify_epsilon_frac,
    )

    # Precedence: explicit UI field > dimension parsed from the prompt > default width.
    if target_size_mm is not None:
        value_mm, axis = target_size_mm, None
    else:
        value_mm, axis = parse_target_size_mm(prompt) or (settings.sketch_default_width_mm, None)
    contours = _scale_to_target(contours, value_mm, axis)

    _, _, width, height = _bbox(contours)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_dxf(contours, out_dir / "model.dxf")
    _write_svg(contours, width, height, out_dir / "preview.svg")

    return MeshInfo(
        dimensions_mm={"x": round(width, 2), "y": round(height, 2), "z": 0.0},
        volume_mm3=0.0,
        watertight=True,
        warnings=[],
    )
