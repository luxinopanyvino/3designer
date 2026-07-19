import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.deps import store
from app.services.mesh_service import convert_stl_to_3mf

router = APIRouter(prefix="/sessions", tags=["export"])

MEDIA_TYPES = {
    "stl": "model/stl",
    "3mf": "model/3mf",
    "dxf": "application/dxf",
    "svg": "image/svg+xml",
}

FILENAMES = {
    "stl": "model.stl",
    "dxf": "model.dxf",
    "svg": "preview.svg",
}


@router.get("/{session_id}/export")
async def export_model(session_id: str, format: str = "stl", version: str = "latest"):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.versions:
        raise HTTPException(status_code=404, detail="No model generated yet")
    if format not in MEDIA_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported format '{format}'")

    number = session.versions[-1].version if version == "latest" else int(version)
    vdir = store.version_dir(session_id, number)
    filename = f"model_v{number}.{format}"

    if format == "3mf":
        stl_path = vdir / "model.stl"
        if not stl_path.exists():
            raise HTTPException(status_code=404, detail="Version files not found")
        data = await asyncio.to_thread(convert_stl_to_3mf, stl_path)
        return Response(
            content=data,
            media_type=MEDIA_TYPES["3mf"],
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    path = vdir / FILENAMES[format]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Version files not found")
    return FileResponse(path, media_type=MEDIA_TYPES[format], filename=filename)
