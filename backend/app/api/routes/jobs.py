"""Job status + result endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import (
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
    JobSummary,
)
from app.services.job_store import JobStore, get_job_store

router = APIRouter(prefix="/api/job", tags=["jobs"])


def _report_url(job_id: str, kind: str) -> str:
    return f"/api/report/{job_id}/{kind}"


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Poll the status of a processing job",
)
def get_job_status(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> JobStatusResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return JobStatusResponse(
        job_id=record.job_id,
        status=record.status,
        pct=record.pct,
        message=record.message,
    )


@router.get(
    "/{job_id}/result",
    response_model=JobResultResponse,
    summary="Fetch the full summary + report URLs for a completed job",
)
def get_job_result(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> JobResultResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if record.status != JobStatus.COMPLETED or record.summary is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Job is in status '{record.status.value}', not completed",
        )
    return JobResultResponse(
        job_id=record.job_id,
        status=record.status,
        summary=JobSummary(**record.summary),
        report_csv_url=_report_url(record.job_id, "csv"),
        report_xlsx_url=_report_url(record.job_id, "xlsx"),
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel an in-flight job and clean up its artifacts",
)
def cancel_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
) -> None:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    store.cancel(job_id)
    if record.upload_path.exists():
        record.upload_path.unlink(missing_ok=True)
    return None
