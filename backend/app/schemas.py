from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    version: int | None = None
    error: bool = False
    created_at: str


class VersionOut(BaseModel):
    version: int
    model_url: str
    code_url: str
    dimensions_mm: dict[str, float]
    volume_mm3: float
    watertight: bool
    warnings: list[str]
    created_at: str


class SessionCreatedOut(BaseModel):
    id: str
    created_at: str


class SessionOut(BaseModel):
    id: str
    created_at: str
    messages: list[MessageOut]
    versions: list[VersionOut]


class MessageIn(BaseModel):
    content: str


class JobAcceptedOut(BaseModel):
    job_id: str


class OllamaHealth(BaseModel):
    reachable: bool
    models: list[str] = []
    code_model_present: bool = False


class HealthOut(BaseModel):
    status: str
    ollama: OllamaHealth
    export_formats: list[str]
    bed_size_mm: float
