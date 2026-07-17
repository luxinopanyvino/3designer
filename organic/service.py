"""PrintCAD organic microservice: photo -> neural 3D mesh.

Runs as a separate process with its own heavy PyTorch/CUDA environment:

    cd organic
    uv run uvicorn service:app --port 8001

Engines (ORGANIC_ENGINE env var):
  - trellis (default): microsoft/TRELLIS-image-large (~4.5 GB weights +
    DINOv2 ~1.2 GB, downloaded from Hugging Face on first /generate).
    Much higher detail than TripoSR; ~6 GB VRAM resident.
  - triposr: legacy stabilityai/TripoSR (~1.4 GB), kept as fallback.

Returns a raw binary STL; the main backend repairs/scales/places it.
"""

import asyncio
import io
import os
import random
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))  # shims: torchmcubes (TripoSR), xformers (TRELLIS)

ENGINE = os.environ.get("ORGANIC_ENGINE", "trellis").lower()

if ENGINE == "trellis":
    sys.path.insert(0, str(ROOT / "vendor" / "TRELLIS"))
    os.environ.setdefault("ATTN_BACKEND", "sdpa")  # dense attention: native torch
    os.environ.setdefault("SPARSE_ATTN_BACKEND", "xformers")  # -> local SDPA shim
    os.environ.setdefault("SPCONV_ALGO", "native")  # skip slow first-run autotune
    os.environ.setdefault("XFORMERS_DISABLED", "1")  # DINOv2: pure-torch path
    # trellis.pipelines imports the (unused) text-to-3D pipeline, which needs
    # open3d at module level (incl. o3d.geometry.TriangleMesh in annotations);
    # a stub keeps the import graph mesh-only.
    _o3d = types.ModuleType("open3d")
    _o3d.geometry = types.SimpleNamespace(TriangleMesh=object)
    sys.modules.setdefault("open3d", _o3d)
else:
    sys.path.insert(0, str(ROOT / "vendor" / "TripoSR"))

import numpy as np
import torch
import trimesh
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

app = FastAPI(title="PrintCAD Organic")

MAX_FACES = 500_000  # decimation cap; keeps STL/GLB viewer-friendly

# TripoSR engine
MC_RESOLUTION = 256
FOREGROUND_RATIO = 0.85
CHUNK_SIZE = 8192

_state: dict = {}
_lock = asyncio.Lock()


def _get_trellis():
    if "trellis" not in _state:
        from trellis.pipelines import TrellisImageTo3DPipeline

        pipeline = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
        pipeline.cuda()
        _state["trellis"] = pipeline
    return _state["trellis"]


def _generate_trellis(image_bytes: bytes) -> bytes:
    import fast_simplification

    pipeline = _get_trellis()
    image = Image.open(io.BytesIO(image_bytes))
    seed = random.randint(0, 2**31 - 1)
    outputs = pipeline.run(image, seed=seed, formats=["mesh"])
    result = outputs["mesh"][0]
    if not result.success:
        raise RuntimeError("TRELLIS produced an empty mesh")

    vertices = result.vertices.float().cpu().numpy().astype(np.float64)
    faces = result.faces.cpu().numpy().astype(np.int64)
    if len(faces) > MAX_FACES:
        vertices, faces = fast_simplification.simplify(
            vertices, faces, target_count=MAX_FACES
        )
    return trimesh.Trimesh(vertices, faces, process=False).export(file_type="stl")


def _get_triposr():
    if "triposr" not in _state:
        import rembg
        from tsr.system import TSR

        model = TSR.from_pretrained(
            "stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt"
        )
        model.renderer.set_chunk_size(CHUNK_SIZE)
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        model.to(device)
        _state["triposr"] = (model, device)
        _state["rembg"] = rembg.new_session()
    return _state["triposr"]


def _generate_triposr(image_bytes: bytes) -> bytes:
    from tsr.utils import remove_background, resize_foreground

    model, device = _get_triposr()

    image = remove_background(Image.open(io.BytesIO(image_bytes)), _state["rembg"])
    image = resize_foreground(image, FOREGROUND_RATIO)
    array = np.array(image).astype(np.float32) / 255.0
    array = array[:, :, :3] * array[:, :, 3:4] + (1 - array[:, :, 3:4]) * 0.5
    image = Image.fromarray((array * 255.0).astype(np.uint8))

    with torch.no_grad():
        scene_codes = model([image], device=device)
    meshes = model.extract_mesh(scene_codes, False, resolution=MC_RESOLUTION)
    return meshes[0].export(file_type="stl")


def _generate_sync(image_bytes: bytes) -> bytes:
    if ENGINE == "trellis":
        with torch.no_grad():
            return _generate_trellis(image_bytes)
    return _generate_triposr(image_bytes)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "engine": ENGINE,
        "cuda": torch.cuda.is_available(),
        "model_loaded": ENGINE in _state,
    }


@app.post("/generate")
async def generate(image: UploadFile = File(...)):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image")
    async with _lock:  # one reconstruction at a time; VRAM is shared with Ollama
        try:
            stl = await asyncio.to_thread(_generate_sync, image_bytes)
        except Exception as exc:  # noqa: BLE001 - surfaced to the main backend
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    return Response(content=stl, media_type="model/stl")
