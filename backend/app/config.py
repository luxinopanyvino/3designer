from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    model_vision: str = "qwen3-vl:8b"
    bed_size_mm: float = 220.0
    max_height_mm: float = 250.0
    organic_service_url: str = "http://localhost:8001"
    organic_timeout_s: int = 600
    organic_default_size_mm: float = 80.0
    sketch_default_width_mm: float = 100.0
    sketch_min_contour_area_frac: float = 0.0005
    sketch_simplify_epsilon_frac: float = 0.005
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"

    model_config = {"env_prefix": "PRINTCAD_"}


settings = Settings()
