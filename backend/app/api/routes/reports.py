"""Report download endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.services.job_store import JobStore, get_job_store

router = APIRouter(prefix="/api/report", tags=["reports"])

_MEDIA_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.get(
    "/{job_id}/{kind}",
    summary="Download a generated CSV or XLSX report",
)
def download_report(
    job_id: str,
    kind: Literal["csv", "xlsx"],
    store: JobStore = Depends(get_job_store),
) -> FileResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    path = record.report_csv if kind == "csv" else record.report_xlsx
    if path is None or not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{kind.upper()} report not ready")

    return FileResponse(
        path=path,
        media_type=_MEDIA_TYPES[kind],
        filename=f"drone-traffic-{job_id}.{kind}",
    )
