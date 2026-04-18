"""End-to-end CV pipeline: decode → detect → track → count → report.

This module exposes a single entry point, :func:`run_pipeline`, which is
scheduled by ``BackgroundTasks`` after a successful upload. The function runs
the heavy CV work in a thread executor so the FastAPI event loop stays free
for HTTP/WebSocket traffic. Progress and per-frame previews are pushed to the
job's WebSocket queue via :class:`~app.services.job_store.JobStore`.
"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import asdict
from typing import Any

import cv2
import numpy as np
from loguru import logger

from app.config import get_settings
from app.core.counter import VehicleCounter
from app.core.detector import YoloDetector
from app.core.tracker import Track, VehicleTracker
from app.schemas import JobStatus
from app.services.job_store import JobStore, get_job_store
from app.services.reporter import generate_reports
from app.utils.video import apply_clahe, iter_frames, probe_video, resize_preserving_aspect

# Annotator colours per class (BGR).
_COLORS: dict[str, tuple[int, int, int]] = {
    "car": (66, 165, 245),
    "truck": (244, 67, 54),
    "bus": (156, 39, 176),
    "motorcycle": (76, 175, 80),
}
_DEFAULT_COLOR = (200, 200, 200)


def _draw_overlay(
    frame: np.ndarray,
    tracks: list[Track],
    line_y: float,
    counts: dict[str, int],
    total: int,
) -> np.ndarray:
    """Draw bounding boxes, IDs, the counting line, and a HUD."""
    out = frame.copy()
    h, w = out.shape[:2]
    line_y_int = int(line_y)
    cv2.line(out, (0, line_y_int), (w, line_y_int), (0, 255, 255), 2, cv2.LINE_AA)

    for t in tracks:
        x1, y1, x2, y2 = (int(v) for v in t.bbox)
        color = _COLORS.get(t.class_name, _DEFAULT_COLOR)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"#{t.track_id} {t.class_name} {t.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(
            out, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
        )

    pad = 10
    hud_lines = [f"TOTAL: {total}"] + [
        f"{cls}: {counts.get(cls, 0)}" for cls in ("car", "truck", "bus", "motorcycle")
    ]
    box_h = 22 * len(hud_lines) + pad
    cv2.rectangle(out, (pad, pad), (220, pad + box_h), (0, 0, 0), -1)
    for i, line in enumerate(hud_lines):
        cv2.putText(
            out, line, (pad + 8, pad + 22 * (i + 1)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA,
        )
    return out


def _encode_jpeg(frame: np.ndarray, quality: int = 65) -> str:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _process(job_id: str, store: JobStore) -> None:
    """The synchronous pipeline body executed inside a worker thread."""
    settings = get_settings()
    record = store.get(job_id)
    if record is None:
        logger.error("Pipeline started for unknown job {}", job_id)
        return

    store.update(job_id, status=JobStatus.PROCESSING, pct=0.0, message="Loading model")
    store.publish(job_id, {"type": "progress", "pct": 0, "processed": 0, "total": 0})

    try:
        meta = probe_video(record.upload_path)
        logger.info(
            "Job {}: {}x{} @ {:.2f}fps, {} frames ({:.2f}s)",
            job_id, meta.width, meta.height, meta.fps, meta.frame_count, meta.duration_seconds,
        )

        detector = YoloDetector.get(settings.yolo_model, settings.conf_threshold)
        tracker = VehicleTracker(
            track_buffer=settings.track_buffer,
            frame_rate=max(1, int(round(meta.fps))),
        )
        counter: VehicleCounter | None = None
        per_detection_log: list[dict[str, Any]] = []

        start_ts = time.time()
        processed = 0
        # Number of frames we will actually process (every Nth original frame).
        skip = max(1, settings.frame_skip)
        target_total = max(1, meta.frame_count // skip if meta.frame_count > 0 else 1)
        last_progress_emit = 0.0

        for frame_idx, ts, frame in iter_frames(record.upload_path, frame_skip=skip):
            if record.cancel_flag.is_set():
                logger.info("Job {} cancelled by user", job_id)
                store.update(job_id, status=JobStatus.CANCELLED, message="Cancelled by user")
                store.publish(job_id, {"type": "error", "message": "Cancelled"})
                return

            resized, _ = resize_preserving_aspect(frame, settings.resize_max)
            equalised = apply_clahe(resized)
            detections = detector.detect(equalised)
            tracks = tracker.update(detections)

            if counter is None:
                counter = VehicleCounter.from_frame_size(resized.shape[0], line_y_ratio=0.5)

            new_events = counter.update(tracks, frame_idx=frame_idx, timestamp=ts)

            for t in tracks:
                per_detection_log.append(
                    {
                        "frame": frame_idx,
                        "timestamp": round(ts, 3),
                        "track_id": t.track_id,
                        "class": t.class_name,
                        "confidence": round(t.confidence, 4),
                        "bbox_x1": round(t.bbox[0], 2),
                        "bbox_y1": round(t.bbox[1], 2),
                        "bbox_x2": round(t.bbox[2], 2),
                        "bbox_y2": round(t.bbox[3], 2),
                        "counted_this_frame": any(e.track_id == t.track_id for e in new_events),
                    }
                )

            processed += 1
            pct = min(100.0, 100.0 * processed / target_total)

            now = time.time()
            should_stream = (processed % settings.frame_stream_every == 0)
            should_progress = (now - last_progress_emit) >= 0.25 or pct >= 100.0

            if should_stream:
                annotated = _draw_overlay(
                    resized, tracks, counter.line_y, counter.by_type(), counter.total
                )
                jpeg = _encode_jpeg(annotated)
                if jpeg:
                    store.publish(job_id, {"type": "frame", "frame_idx": frame_idx, "data": jpeg})

            if should_progress:
                last_progress_emit = now
                store.update(job_id, pct=pct, message="Processing")
                store.publish(
                    job_id,
                    {
                        "type": "progress",
                        "pct": round(pct, 2),
                        "processed": processed,
                        "total": target_total,
                    },
                )

        duration = time.time() - start_ts
        if counter is None:
            counter = VehicleCounter.from_frame_size(meta.height)

        report_csv, report_xlsx = generate_reports(
            job_id=job_id,
            out_dir=settings.report_dir,
            detections=per_detection_log,
            crossings=[asdict(c) for c in counter.crossings],
            summary={
                "total_vehicles": counter.total,
                "by_type": counter.by_type(),
                "processing_seconds": round(duration, 3),
                "frame_count": meta.frame_count,
                "fps": round(meta.fps, 3),
                "duration_seconds": round(meta.duration_seconds, 3),
                "frames_processed": processed,
                "frame_skip": skip,
            },
        )

        summary = {
            "total_vehicles": counter.total,
            "by_type": counter.by_type(),
            "processing_seconds": round(duration, 3),
            "frame_count": meta.frame_count,
            "fps": round(meta.fps, 3),
            "duration_seconds": round(meta.duration_seconds, 3),
        }
        store.update(
            job_id,
            status=JobStatus.COMPLETED,
            pct=100.0,
            message="Completed",
            summary=summary,
            report_csv=report_csv,
            report_xlsx=report_xlsx,
        )
        store.publish(
            job_id,
            {
                "type": "complete",
                "summary": summary,
                "report_csv_url": f"/api/report/{job_id}/csv",
                "report_xlsx_url": f"/api/report/{job_id}/xlsx",
            },
        )
        logger.info(
            "Job {} done: {} vehicles in {:.2f}s (real video {:.2f}s)",
            job_id, counter.total, duration, meta.duration_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job {} failed: {}", job_id, exc)
        store.update(job_id, status=JobStatus.FAILED, message=str(exc))
        store.publish(job_id, {"type": "error", "message": str(exc)})


async def run_pipeline(job_id: str) -> None:
    """Async wrapper used by FastAPI ``BackgroundTasks``."""
    store = get_job_store()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _process, job_id, store)
