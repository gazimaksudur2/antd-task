"""Video I/O helpers: validation, frame iteration, resizing."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    width: int
    height: int
    duration_seconds: float


def probe_video(path: Path) -> VideoMeta:
    """Open the file with OpenCV and read basic metadata.

    Raises :class:`ValueError` if the file cannot be decoded as video.
    """
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError("File could not be decoded as a video stream")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if width == 0 or height == 0:
            raise ValueError("Video has zero-size frames")
        if fps <= 0:
            fps = 30.0  # sane fallback for malformed metadata
        duration = frame_count / fps if fps > 0 else 0.0
        return VideoMeta(
            fps=fps,
            frame_count=frame_count,
            width=width,
            height=height,
            duration_seconds=duration,
        )
    finally:
        cap.release()


def resize_preserving_aspect(frame: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    """Resize so the longest side equals *max_side*; return new frame + scale.

    The scale factor is ``new / original`` so callers can map detection
    coordinates back to the original frame if desired.
    """
    h, w = frame.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return frame, 1.0
    scale = max_side / float(longest)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def apply_clahe(frame_bgr: np.ndarray) -> np.ndarray:
    """Lightweight contrast equalisation in LAB space; helps with sun glare."""
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l_channel)
    return cv2.cvtColor(cv2.merge([l_eq, a, b]), cv2.COLOR_LAB2BGR)


def iter_frames(
    path: Path,
    frame_skip: int = 1,
) -> Iterator[tuple[int, float, np.ndarray]]:
    """Yield ``(frame_idx, timestamp_seconds, frame_bgr)`` tuples.

    ``frame_skip`` of ``N`` keeps every Nth frame (i.e. ``1`` means every
    frame, ``2`` means every other, etc.). Frame indices and timestamps
    correspond to the *original* video timeline so reports stay accurate.
    """
    if frame_skip < 1:
        frame_skip = 1
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("File could not be decoded as a video stream")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    try:
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_skip == 0:
                ts = frame_idx / fps if fps > 0 else 0.0
                yield frame_idx, ts, frame
            frame_idx += 1
    finally:
        cap.release()
