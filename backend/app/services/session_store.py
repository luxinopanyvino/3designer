"""Per-session state: message history + immutable model versions.

In-memory dict flushed to data/sessions/{id}/session.json after every
mutation, lazily reloaded after a restart. One asyncio.Lock per session
serializes generations.
"""

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.services.mesh_service import MeshInfo


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Message:
    id: int
    role: str  # "user" | "assistant"
    content: str
    version: int | None = None
    error: bool = False
    image_url: str | None = None
    created_at: str = field(default_factory=_now)


@dataclass
class Version:
    version: int
    dimensions_mm: dict[str, float]
    volume_mm3: float
    watertight: bool
    warnings: list[str] = field(default_factory=list)
    source: str = "cad"  # "organic" (neural mesh) | "sketch" (2D DXF); legacy "cad" tolerated
    created_at: str = field(default_factory=_now)


@dataclass
class Session:
    id: str
    created_at: str = field(default_factory=_now)
    messages: list[Message] = field(default_factory=list)
    versions: list[Version] = field(default_factory=list)


class SessionStore:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def version_dir(self, session_id: str, version: int) -> Path:
        return self.session_dir(session_id) / f"v{version}"

    def lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    def create(self) -> Session:
        session = Session(id=uuid.uuid4().hex[:12])
        self._sessions[session.id] = session
        self.save(session)
        return session

    def get(self, session_id: str) -> Session | None:
        if session_id in self._sessions:
            return self._sessions[session_id]
        path = self.session_dir(session_id) / "session.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        session = Session(
            id=raw["id"],
            created_at=raw["created_at"],
            messages=[Message(**m) for m in raw["messages"]],
            versions=[Version(**v) for v in raw["versions"]],
        )
        self._sessions[session_id] = session
        return session

    def save(self, session: Session) -> None:
        sdir = self.session_dir(session.id)
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "session.json").write_text(
            json.dumps(asdict(session), indent=2), encoding="utf-8"
        )

    def add_message(
        self,
        session: Session,
        role: str,
        content: str,
        version: int | None = None,
        error: bool = False,
        image_url: str | None = None,
    ) -> Message:
        message = Message(
            id=len(session.messages) + 1,
            role=role,
            content=content,
            version=version,
            error=error,
            image_url=image_url,
        )
        session.messages.append(message)
        self.save(session)
        return message

    def add_version(self, session: Session, mesh_info: MeshInfo, source: str = "cad") -> Version:
        version = Version(
            version=len(session.versions) + 1,
            dimensions_mm=mesh_info.dimensions_mm,
            volume_mm3=mesh_info.volume_mm3,
            watertight=mesh_info.watertight,
            warnings=list(mesh_info.warnings),
            source=source,
        )
        session.versions.append(version)
        self.save(session)
        return version

    def next_version_number(self, session: Session) -> int:
        return len(session.versions) + 1
