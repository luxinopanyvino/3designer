"""In-memory generation jobs with replayable event logs for SSE.

Events are appended to a list (never removed while the job lives), so a
client that connects late still receives the full stream from the start.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field

TERMINAL_EVENTS = {"completed", "error"}


@dataclass
class Job:
    id: str
    session_id: str
    events: list[tuple[str, dict]] = field(default_factory=list)
    new_event: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def done(self) -> bool:
        return bool(self.events) and self.events[-1][0] in TERMINAL_EVENTS


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._running_by_session: dict[str, str] = {}

    def create(self, session_id: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], session_id=session_id)
        self._jobs[job.id] = job
        self._running_by_session[session_id] = job.id
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def session_busy(self, session_id: str) -> bool:
        job_id = self._running_by_session.get(session_id)
        if job_id is None:
            return False
        job = self._jobs.get(job_id)
        return job is not None and not job.done

    async def emit(self, job: Job, event: str, data: dict) -> None:
        job.events.append((event, data))
        job.new_event.set()

    async def stream(self, job: Job):
        """Async generator of sse-starlette event dicts; ends after a terminal event."""
        index = 0
        while True:
            if index < len(job.events):
                name, data = job.events[index]
                index += 1
                yield {"event": name, "data": json.dumps(data)}
                if name in TERMINAL_EVENTS:
                    return
                continue
            job.new_event.clear()
            if index < len(job.events):
                continue
            await job.new_event.wait()
