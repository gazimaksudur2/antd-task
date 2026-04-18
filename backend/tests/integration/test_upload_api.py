"""Integration tests for the FastAPI upload + jobs endpoints.

These tests stub out the heavyweight pieces (the YOLO pipeline and the
file-content validators) so they run on a CI runner without the model
weights and without ffmpeg. The contract under test is the HTTP API shape.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.services import job_store as job_store_module
from app.services.job_store import JobStore


@pytest.fixture
def app_client(tmp_path, monkeypatch) -> TestClient:
    # Isolate uploads / reports to a temp dir per test.
    settings = get_settings()
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "report_dir", tmp_path / "reports")
    settings.ensure_dirs()

    # Reset the singleton job store between tests.
    monkeypatch.setattr(job_store_module, "_store", JobStore())

    # Stub validators / probes so we do not need a real video on disk.
    from app.api.routes import upload as upload_module

    monkeypatch.setattr(upload_module, "validate_video_bytes", lambda head, name: "video/mp4")

    def _fake_probe(_path: Path):
        from app.utils.video import VideoMeta

        return VideoMeta(fps=30.0, frame_count=300, width=1280, height=720, duration_seconds=10.0)

    monkeypatch.setattr(upload_module, "probe_video", _fake_probe)

    # No-op pipeline so we don't trigger model load.
    async def _noop(_job_id: str) -> None:
        return None

    monkeypatch.setattr(upload_module, "run_pipeline", _noop)

    from app.main import create_app

    return TestClient(create_app())


def test_health(app_client: TestClient):
    res = app_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_upload_returns_job_id(app_client: TestClient):
    payload = io.BytesIO(b"\x00" * 2048)
    res = app_client.post(
        "/api/upload",
        files={"file": ("clip.mp4", payload, "video/mp4")},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert "job_id" in data
    assert data["filename"] == "clip.mp4"
    assert data["size_bytes"] > 0


def test_upload_rejects_invalid_filetype(app_client: TestClient, monkeypatch):
    from app.api.routes import upload as upload_module
    from app.utils.file_validation import InvalidVideoFile

    def _bad(_head: bytes, _name: str) -> str:
        raise InvalidVideoFile("Unsupported video format")

    monkeypatch.setattr(upload_module, "validate_video_bytes", _bad)

    res = app_client.post(
        "/api/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert res.status_code == 422
    assert "Unsupported" in res.json()["detail"]


def test_status_endpoint_after_upload(app_client: TestClient):
    res = app_client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(b"\x00" * 1024), "video/mp4")},
    )
    job_id = res.json()["job_id"]

    status = app_client.get(f"/api/job/{job_id}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["job_id"] == job_id
    assert body["status"] in {"pending", "processing", "completed"}


def test_status_404_for_unknown_job(app_client: TestClient):
    res = app_client.get("/api/job/does-not-exist/status")
    assert res.status_code == 404


def test_result_409_when_not_completed(app_client: TestClient):
    res = app_client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(b"\x00" * 1024), "video/mp4")},
    )
    job_id = res.json()["job_id"]
    result = app_client.get(f"/api/job/{job_id}/result")
    assert result.status_code == 409


def test_report_404_when_not_ready(app_client: TestClient):
    res = app_client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(b"\x00" * 1024), "video/mp4")},
    )
    job_id = res.json()["job_id"]
    report = app_client.get(f"/api/report/{job_id}/csv")
    assert report.status_code == 404


def test_cancel_job(app_client: TestClient):
    res = app_client.post(
        "/api/upload",
        files={"file": ("clip.mp4", io.BytesIO(b"\x00" * 1024), "video/mp4")},
    )
    job_id = res.json()["job_id"]
    cancel = app_client.delete(f"/api/job/{job_id}")
    assert cancel.status_code == 204
