"""Mesh analysis and STL->GLB conversion with trimesh.

Degenerate geometry raises DegenerateMeshError, which the generation loop
treats as a repairable error (fed back to the LLM). Printability issues that
are still valid models (bed overflow, steep overhangs) become warnings.
"""

import io
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh

MAX_DIMENSION_MM = 1e6
OVERHANG_ANGLE_DEG = 45.0
OVERHANG_WARN_FRACTION = 0.05
BED_CONTACT_TOLERANCE_MM = 0.5


class DegenerateMeshError(Exception):
    """The mesh exists but is unusable; message is aimed at the LLM repair prompt."""


@dataclass
class MeshInfo:
    dimensions_mm: dict[str, float]
    volume_mm3: float
    watertight: bool
    warnings: list[str] = field(default_factory=list)


def analyze_stl(stl_path: Path, bed_size_mm: float = 220.0, max_height_mm: float = 250.0) -> MeshInfo:
    mesh = trimesh.load_mesh(stl_path)
    if mesh.is_empty or len(mesh.faces) == 0:
        raise DegenerateMeshError("The exported mesh is empty (no faces).")

    extents = mesh.bounds[1] - mesh.bounds[0]
    if float(extents.max()) > MAX_DIMENSION_MM:
        raise DegenerateMeshError(
            f"The model is absurdly large ({extents.max():.0f} mm on one side); "
            "check the dimension parameters."
        )
    if float(extents.min()) <= 1e-6:
        raise DegenerateMeshError("The model has zero thickness on at least one axis.")

    watertight = bool(mesh.is_watertight)
    volume = float(abs(mesh.volume)) if watertight else 0.0
    if watertight and volume <= 1e-6:
        raise DegenerateMeshError("The model has zero volume.")

    warnings: list[str] = []
    if not watertight:
        warnings.append("Mesh is not watertight; the slicer may need to repair it.")
    if extents[0] > bed_size_mm or extents[1] > bed_size_mm:
        warnings.append(
            f"Model footprint {extents[0]:.1f}x{extents[1]:.1f} mm exceeds the "
            f"{bed_size_mm:.0f}x{bed_size_mm:.0f} mm build plate."
        )
    if extents[2] > max_height_mm:
        warnings.append(f"Model height {extents[2]:.1f} mm exceeds {max_height_mm:.0f} mm.")

    overhang = _overhang_fraction(mesh)
    if overhang > OVERHANG_WARN_FRACTION:
        warnings.append(
            f"About {overhang:.0%} of the surface overhangs more than "
            f"{OVERHANG_ANGLE_DEG:.0f} degrees; supports may be needed."
        )

    return MeshInfo(
        dimensions_mm={
            "x": round(float(extents[0]), 2),
            "y": round(float(extents[1]), 2),
            "z": round(float(extents[2]), 2),
        },
        volume_mm3=round(volume, 2),
        watertight=watertight,
        warnings=warnings,
    )


def _overhang_fraction(mesh: trimesh.Trimesh) -> float:
    """Fraction of surface area facing down steeper than OVERHANG_ANGLE_DEG,
    excluding faces resting on the build plate (z ~ 0)."""
    normals = mesh.face_normals
    threshold = -math.cos(math.radians(OVERHANG_ANGLE_DEG))
    steep_down = normals[:, 2] < threshold

    centroids_z = mesh.triangles_center[:, 2]
    min_z = float(mesh.bounds[0][2])
    on_bed = centroids_z < (min_z + BED_CONTACT_TOLERANCE_MM)

    overhang_area = float(mesh.area_faces[steep_down & ~on_bed].sum())
    total_area = float(mesh.area)
    return overhang_area / total_area if total_area > 0 else 0.0


def convert_stl_to_glb(stl_path: Path, glb_path: Path) -> None:
    """GLB stays in millimeters; the frontend scene uses 1 unit = 1 mm."""
    mesh = trimesh.load_mesh(stl_path)
    glb_path.write_bytes(mesh.export(file_type="glb"))


def convert_stl_to_3mf(stl_path: Path) -> bytes:
    mesh = trimesh.load_mesh(stl_path)
    return mesh.export(file_type="3mf")


def supported_export_formats() -> list[str]:
    formats = ["stl", "step"]
    try:
        trimesh.creation.box(extents=(1, 1, 1)).export(file_obj=io.BytesIO(), file_type="3mf")
        formats.append("3mf")
    except BaseException:
        pass
    return formats
