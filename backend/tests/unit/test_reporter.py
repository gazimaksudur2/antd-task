"""Unit tests for CSV/XLSX report generation."""

from __future__ import annotations

import csv

import pandas as pd

from app.services.reporter import DETECTION_COLUMNS, generate_reports


def _summary() -> dict:
    return {
        "total_vehicles": 3,
        "by_type": {"car": 2, "truck": 1, "bus": 0, "motorcycle": 0},
        "processing_seconds": 12.34,
        "frame_count": 900,
        "fps": 30.0,
        "duration_seconds": 30.0,
        "frames_processed": 450,
        "frame_skip": 2,
    }


def _detections() -> list[dict]:
    return [
        {
            "frame": 10,
            "timestamp": 0.333,
            "track_id": 1,
            "class": "car",
            "confidence": 0.91,
            "bbox_x1": 10.0,
            "bbox_y1": 12.0,
            "bbox_x2": 50.0,
            "bbox_y2": 60.0,
            "counted_this_frame": True,
        },
        {
            "frame": 20,
            "timestamp": 0.666,
            "track_id": 2,
            "class": "truck",
            "confidence": 0.85,
            "bbox_x1": 100.0,
            "bbox_y1": 110.0,
            "bbox_x2": 200.0,
            "bbox_y2": 220.0,
            "counted_this_frame": False,
        },
    ]


def _crossings() -> list[dict]:
    return [
        {"track_id": 1, "class_name": "car", "frame_idx": 10, "timestamp": 0.333},
        {"track_id": 2, "class_name": "truck", "frame_idx": 20, "timestamp": 0.666},
    ]


def test_generate_reports_creates_both_files(tmp_path):
    csv_path, xlsx_path = generate_reports(
        job_id="abc123",
        out_dir=tmp_path,
        detections=_detections(),
        crossings=_crossings(),
        summary=_summary(),
    )
    assert csv_path.exists()
    assert xlsx_path.exists()
    assert csv_path.name == "abc123.csv"
    assert xlsx_path.name == "abc123.xlsx"


def test_csv_has_expected_columns_and_rows(tmp_path):
    csv_path, _ = generate_reports(
        job_id="abc123",
        out_dir=tmp_path,
        detections=_detections(),
        crossings=_crossings(),
        summary=_summary(),
    )
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert reader.fieldnames == DETECTION_COLUMNS
    assert len(rows) == 2
    assert rows[0]["class"] == "car"
    assert rows[1]["class"] == "truck"


def test_xlsx_has_three_sheets_and_summary_metrics(tmp_path):
    _, xlsx_path = generate_reports(
        job_id="abc123",
        out_dir=tmp_path,
        detections=_detections(),
        crossings=_crossings(),
        summary=_summary(),
    )
    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    assert set(sheets.keys()) == {"Summary", "Crossings", "Detections"}

    summary_df = sheets["Summary"]
    assert {"Metric", "Value"} == set(summary_df.columns)
    metrics = dict(zip(summary_df["Metric"], summary_df["Value"], strict=False))
    assert metrics["Total vehicles"] == 3
    assert metrics["Count: car"] == 2
    assert metrics["Count: truck"] == 1

    detections_df = sheets["Detections"]
    assert len(detections_df) == 2
    crossings_df = sheets["Crossings"]
    assert len(crossings_df) == 2


def test_empty_inputs_produce_valid_files_with_headers(tmp_path):
    csv_path, xlsx_path = generate_reports(
        job_id="empty",
        out_dir=tmp_path,
        detections=[],
        crossings=[],
        summary={
            "total_vehicles": 0,
            "by_type": {},
            "processing_seconds": 0.0,
            "frame_count": 0,
            "fps": 0.0,
            "duration_seconds": 0.0,
        },
    )
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0] == DETECTION_COLUMNS
    assert len(rows) == 1  # header only

    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    assert sheets["Detections"].empty
    assert sheets["Crossings"].empty
