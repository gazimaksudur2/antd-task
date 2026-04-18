"""CSV + XLSX report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

DETECTION_COLUMNS = [
    "frame",
    "timestamp",
    "track_id",
    "class",
    "confidence",
    "bbox_x1",
    "bbox_y1",
    "bbox_x2",
    "bbox_y2",
    "counted_this_frame",
]

CROSSING_COLUMNS = ["track_id", "class_name", "frame_idx", "timestamp"]


def _summary_dataframe(summary: dict[str, Any]) -> pd.DataFrame:
    by_type = summary.get("by_type", {}) or {}
    rows = [
        ("Total vehicles", summary.get("total_vehicles", 0)),
        ("Processing seconds", summary.get("processing_seconds", 0.0)),
        ("Video duration (s)", summary.get("duration_seconds", 0.0)),
        ("Video FPS", summary.get("fps", 0.0)),
        ("Frame count", summary.get("frame_count", 0)),
        ("Frames processed", summary.get("frames_processed", 0)),
        ("Frame skip", summary.get("frame_skip", 1)),
    ]
    for cls in ("car", "truck", "bus", "motorcycle"):
        rows.append((f"Count: {cls}", int(by_type.get(cls, 0))))
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def generate_reports(
    job_id: str,
    out_dir: Path,
    detections: list[dict[str, Any]],
    crossings: list[dict[str, Any]],
    summary: dict[str, Any],
) -> tuple[Path, Path]:
    """Write a per-job CSV (detections) and XLSX (Summary + Detections + Crossings).

    Returns the resolved output paths in the order ``(csv, xlsx)``.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    detections_df = (
        pd.DataFrame(detections, columns=DETECTION_COLUMNS)
        if detections
        else pd.DataFrame(columns=DETECTION_COLUMNS)
    )
    crossings_df = (
        pd.DataFrame(crossings, columns=CROSSING_COLUMNS)
        if crossings
        else pd.DataFrame(columns=CROSSING_COLUMNS)
    )
    summary_df = _summary_dataframe(summary)

    csv_path = out_dir / f"{job_id}.csv"
    detections_df.to_csv(csv_path, index=False)

    xlsx_path = out_dir / f"{job_id}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        crossings_df.to_excel(writer, sheet_name="Crossings", index=False)
        detections_df.to_excel(writer, sheet_name="Detections", index=False)

    return csv_path, xlsx_path
