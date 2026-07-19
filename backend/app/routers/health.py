from fastapi import APIRouter
from ollama import AsyncClient

from app.config import settings
from app.schemas import HealthOut, OllamaHealth
from app.services.mesh_service import supported_export_formats
from app.services.organic import organic_service_healthy

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health():
    ollama = OllamaHealth(reachable=False)
    try:
        listing = await AsyncClient(host=settings.ollama_host).list()
        models = [m.model for m in listing.models]
        ollama = OllamaHealth(
            reachable=True,
            models=models,
            vision_model_present=settings.model_vision in models,
        )
    except Exception:
        pass

    return HealthOut(
        status="ok",
        ollama=ollama,
        organic_available=await organic_service_healthy(),
        export_formats=supported_export_formats() + ["dxf", "svg"],
        bed_size_mm=settings.bed_size_mm,
    )
