"""Client for the organic (photo -> neural mesh) microservice, plus mesh repair.

The heavy TripoSR/PyTorch stack lives in the separate `organic/` project and is
reached over HTTP. Meshes coming out of neural reconstruction are dirty:
multiple components, holes, flipped normals, arbitrary scale. This module
repairs them and normalizes size/placement before they enter the regular
version pipeline (GLB viewer + STL export). There is no STEP for organic
meshes - they have no B-rep.
"""

import asyncio
from pathlib import Path

import httpx
import trimesh

from app.config import settings
from app.services.mesh_service import analyze_stl
from app.services.session_store import Session  # noqa: F401  (typing docs)


class OrganicServiceError(Exception):
    """The organic microservice is unreachable or failed; message is user-facing."""


async def organic_service_healthy() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{settings.organic_service_url}/health")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


async def request_organic_mesh(image_bytes: bytes) -> bytes:
    """Send the photo to the organic service; returns raw STL bytes."""
    try:
        async with httpx.AsyncClient(timeout=settings.organic_timeout_s) as client:
            r = await client.post(
                f"{settings.organic_service_url}/generate",
                files={"image": ("image.png", image_bytes)},
            )
    except httpx.HTTPError as exc:
        raise OrganicServiceError(
            "El servicio de reconstrucción orgánica no responde "
            f"({settings.organic_service_url}). ¿Está arrancado? ({exc.__class__.__name__})"
        ) from exc
    if r.status_code != 200:
        detail = r.text[:300]
        raise OrganicServiceError(f"El servicio orgánico devolvió un error: {detail}")
    return r.content


def repair_and_normalize(
    raw_stl: bytes, target_size_mm: float
) -> trimesh.Trimesh:
    """Largest component, holes filled, normals fixed, scaled and sitting on the bed."""
    mesh = trimesh.load(
        trimesh.util.wrap_as_stream(raw_stl), file_type="stl", force="mesh"
    )
    if mesh.is_empty or len(mesh.faces) == 0:
        raise OrganicServiceError("La reconstrucción devolvió una malla vacía.")

    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda m: len(m.faces))

    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    trimesh.repair.fill_holes(mesh)
    trimesh.repair.fix_normals(mesh)

    extents = mesh.extents
    if extents.max() <= 0:
        raise OrganicServiceError("La malla reconstruida no tiene volumen.")
    mesh.apply_scale(target_size_mm / float(extents.max()))

    bounds = mesh.bounds
    mesh.apply_translation(
        [
            -(bounds[0][0] + bounds[1][0]) / 2,
            -(bounds[0][1] + bounds[1][1]) / 2,
            -bounds[0][2],
        ]
    )
    return mesh


async def generate_organic_model(*, image_bytes: bytes, target_size_mm: float, out_dir: Path, emit):
    """Full organic pipeline; returns (mesh_info, stl_path, glb_path)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    await emit("status", {"stage": "organic_generating", "attempt": 1})
    raw_stl = await request_organic_mesh(image_bytes)

    def _process():
        mesh = repair_and_normalize(raw_stl, target_size_mm)
        stl_path = out_dir / "model.stl"
        glb_path = out_dir / "model.glb"
        mesh.export(stl_path)
        glb_path.write_bytes(mesh.export(file_type="glb"))
        info = analyze_stl(stl_path, settings.bed_size_mm, settings.max_height_mm)
        return info, stl_path, glb_path

    return await asyncio.to_thread(_process)
