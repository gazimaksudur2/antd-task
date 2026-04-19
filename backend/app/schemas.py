"""Pydantic models used across HTTP/WebSocket boundaries."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadResponse(BaseModel):
    job_id: str = Field(..., description="Unique identifier for the processing job")
    filename: str
    size_bytes: int


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    pct: float = Field(default=0.0, ge=0.0, le=100.0)
    message: str | None = None


class VehicleBreakdown(BaseModel):
    car: int = 0
    truck: int = 0
    bus: int = 0
    motorcycle: int = 0


class JobSummary(BaseModel):
    """Summary returned to UI on completion."""

    total_vehicles: int
    by_type: dict[str, int]
    processing_seconds: float
    frame_count: int
    fps: float
    duration_seconds: float


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    summary: JobSummary
    report_csv_url: str
    report_xlsx_url: str


# --- WebSocket messages ---


class WSProgress(BaseModel):
    type: Literal["progress"] = "progress"
    pct: float
    processed: int
    total: int


class WSFrame(BaseModel):
    type: Literal["frame"] = "frame"
    frame_idx: int
    data: str  # base64 JPEG


class WSComplete(BaseModel):
    type: Literal["complete"] = "complete"
    summary: JobSummary
    report_csv_url: str
    report_xlsx_url: str


class WSError(BaseModel):
    type: Literal["error"] = "error"
    message: str


WSMessage = WSProgress | WSFrame | WSComplete | WSError
