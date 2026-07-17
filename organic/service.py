"""PrintCAD organic microservice: photo -> neural 3D mesh (TripoSR).

Runs as a separate process with its own heavy PyTorch/CUDA environment:

    cd organic
    uv run uvicorn service:app --port 8001

The model (~1.4 GB, stabilityai/TripoSR) is downloaded from Hugging Face on
first use and lazily loaded into VRAM on the first /generate call.
Returns a raw binary STL; the main backend repairs/scales/places it.
"""

import asyncio
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))  # torchmcubes shim (scikit-image based)
sys.path.insert(0, str(ROOT / "vendor" / "TripoSR"))

import numpy as np
import rembg
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

app = FastAPI(title="PrintCAD Organic")

MC_RESOLUTION = 256
FOREGROUND_RATIO = 0.85
CHUNK_SIZE = 8192

_state: dict = {}
_lock = asyncio.Lock()


def _get_model():
    if "model" not in _state:
        from tsr.system import TSR

        model = TSR.from_pretrained(
            "stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt"
        )
        model.renderer.set_chunk_size(CHUNK_SIZE)
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        model.to(device)
        _state["model"] = model
        _state["device"] = device
        _state["rembg"] = rembg.new_session()
    return _state["model"], _state["device"]


def _generate_sync(image_bytes: bytes) -> bytes:
    from tsr.utils import remove_background, resize_foreground

    model, device = _get_model()

    image = remove_background(Image.open(io.BytesIO(image_bytes)), _state["rembg"])
    image = resize_foreground(image, FOREGROUND_RATIO)
    array = np.array(image).astype(np.float32) / 255.0
    array = array[:, :, :3] * array[:, :, 3:4] + (1 - array[:, :, 3:4]) * 0.5
    image = Image.fromarray((array * 255.0).astype(np.uint8))

    with torch.no_grad():
        scene_codes = model([image], device=device)
    meshes = model.extract_mesh(scene_codes, False, resolution=MC_RESOLUTION)
    return meshes[0].export(file_type="stl")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "cuda": torch.cuda.is_available(),
        "model_loaded": "model" in _state,
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
