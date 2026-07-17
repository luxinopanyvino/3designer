from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    model_code: str = "qwen2.5-coder:14b"
    model_vision: str = "qwen3-vl:8b"
    max_repair_attempts: int = 3
    exec_timeout_s: int = 60
    bed_size_mm: float = 220.0
    max_height_mm: float = 250.0
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"

    model_config = {"env_prefix": "PRINTCAD_"}


settings = Settings()
