"""WebSocket endpoint that streams job progress and annotated frames."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.schemas import JobStatus
from app.services.job_store import get_job_store

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/{job_id}")
async def job_stream(websocket: WebSocket, job_id: str) -> None:
    """Stream `progress`, `frame`, `complete`, and `error` messages.

    The server keeps the socket open until the job reaches a terminal state
    or the client disconnects. A queue per job lives in :class:`JobStore`,
    so reconnecting clients receive the cached terminal event immediately.
    """
    await websocket.accept()
    store = get_job_store()
    record = store.get(job_id)
    if record is None:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close(code=1008)
        return

    queue = store.get_or_create_queue(job_id)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
            except TimeoutError:
                latest = store.get(job_id)
                if latest is None:
                    break
                if latest.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                    break
                # Heartbeat so proxies do not idle-close the connection.
                await websocket.send_json(
                    {"type": "progress", "pct": latest.pct, "processed": 0, "total": 0}
                )
                continue

            await websocket.send_json(msg)
            if msg.get("type") in {"complete", "error"}:
                break
    except WebSocketDisconnect:
        logger.info("WS disconnected for job {}", job_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("WS error for job {}: {}", job_id, exc)
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
