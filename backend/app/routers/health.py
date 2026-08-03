from fastapi import APIRouter

from app.config import settings
from app.schemas import HealthOut
from app.services.mesh_service import supported_export_formats
from app.services.organic import organic_service_healthy

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health():
    return HealthOut(
        status="ok",
        organic_available=await organic_service_healthy(),
        export_formats=supported_export_formats() + ["dxf", "svg"],
        bed_size_mm=settings.bed_size_mm,
    )
