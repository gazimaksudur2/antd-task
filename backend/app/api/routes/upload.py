"""POST /api/upload — accept a video, validate it, queue a processing job."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from loguru import logger

from app.config import Settings, get_settings
from app.core.pipeline import run_pipeline
from app.schemas import UploadResponse
from app.services.job_store import JobStore, get_job_store
from app.utils.file_validation import InvalidVideoFile, validate_video_bytes
from app.utils.video import probe_video

router = APIRouter(prefix="/api", tags=["upload"])

CHUNK = 1024 * 1024  # 1 MB per disk write


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a drone video and start processing",
)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="MP4/MOV/AVI/MKV/WebM drone footage"),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Missing filename")

    head = await file.read(512)
    try:
        validate_video_bytes(head, file.filename)
    except InvalidVideoFile as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    job_id = uuid.uuid4().hex
    suffix = Path(file.filename).suffix.lower() or ".mp4"
    upload_path = settings.upload_dir / f"{job_id}{suffix}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        async with aiofiles.open(upload_path, "wb") as out:
            await out.write(head)
            written += len(head)
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > settings.max_upload_bytes:
                    await out.close()
                    upload_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"File exceeds maximum size of {settings.max_upload_bytes} bytes",
                    )
                await out.write(chunk)
    finally:
        await file.close()

    try:
        probe_video(upload_path)
    except ValueError as exc:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    store.create(job_id=job_id, filename=file.filename, upload_path=upload_path)
    logger.info("Created job {} for {} ({} bytes)", job_id, file.filename, written)

    background_tasks.add_task(run_pipeline, job_id)

    return UploadResponse(job_id=job_id, filename=file.filename, size_bytes=written)
