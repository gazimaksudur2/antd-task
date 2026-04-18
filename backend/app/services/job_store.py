"""Thread-safe, in-memory job registry.

For a PoC we keep job state in process memory rather than introducing Redis.
The store is built around two primitives:

* a :class:`threading.RLock`-guarded ``dict`` of jobs (status, results, paths)
* an :class:`asyncio.Queue` per job for streaming WebSocket events from the
  background worker thread to the websocket coroutine.

The queues are created lazily on the first subscriber and survive worker
completion so a late-connecting client still receives the terminal event.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.schemas import JobStatus


@dataclass
class JobRecord:
    job_id: str
    filename: str
    upload_path: Path
    status: JobStatus = JobStatus.PENDING
    pct: float = 0.0
    message: str | None = None
    summary: dict[str, Any] | None = None
    report_csv: Path | None = None
    report_xlsx: Path | None = None
    cancel_flag: threading.Event = field(default_factory=threading.Event)
    created_at: float = field(default_factory=time.time)


class JobStore:
    """Process-wide, thread-safe job registry with per-job event queues."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._terminal_events: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # ----- lifecycle -----

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture the main event loop so worker threads can post messages."""
        self._loop = loop

    # ----- job CRUD -----

    def create(self, job_id: str, filename: str, upload_path: Path) -> JobRecord:
        with self._lock:
            record = JobRecord(job_id=job_id, filename=filename, upload_path=upload_path)
            self._jobs[job_id] = record
            return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            return record

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return False
            record.cancel_flag.set()
            if record.status in {JobStatus.PENDING, JobStatus.PROCESSING}:
                record.status = JobStatus.CANCELLED
            return True

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
            self._queues.pop(job_id, None)
            self._terminal_events.pop(job_id, None)

    # ----- WebSocket queues -----

    def get_or_create_queue(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        with self._lock:
            queue = self._queues.get(job_id)
            if queue is None:
                queue = asyncio.Queue(maxsize=256)
                self._queues[job_id] = queue
                # Replay any cached terminal event for late subscribers.
                terminal = self._terminal_events.get(job_id)
                if terminal is not None:
                    queue.put_nowait(terminal)
            return queue

    def publish(self, job_id: str, message: dict[str, Any]) -> None:
        """Thread-safe publish from a worker thread to the asyncio queue.

        Drops the oldest message if the queue is full so a slow client cannot
        starve the worker.
        """
        if self._loop is None:
            return
        is_terminal = message.get("type") in {"complete", "error"}
        if is_terminal:
            with self._lock:
                self._terminal_events[job_id] = message

        def _put() -> None:
            queue = self._queues.get(job_id)
            if queue is None and is_terminal:
                queue = self.get_or_create_queue(job_id)
            if queue is None:
                return
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(message)

        self._loop.call_soon_threadsafe(_put)


_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store
