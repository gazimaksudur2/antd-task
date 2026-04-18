"""ByteTrack wrapper that maps detections to stable, persistent track IDs.

We use the implementation shipped with ``supervision`` (``sv.ByteTrack``) which
takes a ``sv.Detections`` object built from raw YOLO output and returns the same
detections enriched with ``tracker_id`` values. ID persistence across short
gaps (occlusion, missed detections) is critical for accurate counting and is
controlled by the ``track_buffer`` parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import supervision as sv

from app.core.detector import VEHICLE_CLASSES, Detection


@dataclass(slots=True)
class Track:
    """A tracked detection — a :class:`Detection` plus a stable id."""

    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    class_id: int
    class_name: str

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class VehicleTracker:
    """Thin wrapper around :class:`supervision.ByteTrack`."""

    def __init__(self, track_buffer: int = 30, frame_rate: int = 30) -> None:
        # ``minimum_consecutive_frames=1`` lets us see a track on its first
        # detection; the lost-buffer remembers IDs across gaps.
        self._tracker = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=track_buffer,
            minimum_matching_threshold=0.8,
            frame_rate=frame_rate,
            minimum_consecutive_frames=1,
        )

    def update(self, detections: list[Detection]) -> list[Track]:
        if not detections:
            sv_dets = sv.Detections.empty()
            self._tracker.update_with_detections(sv_dets)
            return []

        xyxy = np.array([d.bbox for d in detections], dtype=np.float32)
        confidence = np.array([d.confidence for d in detections], dtype=np.float32)
        class_id = np.array([d.class_id for d in detections], dtype=int)

        sv_dets = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
        tracked = self._tracker.update_with_detections(sv_dets)

        out: list[Track] = []
        if tracked.tracker_id is None:
            return out
        for box, conf, cls, tid in zip(
            tracked.xyxy,
            tracked.confidence if tracked.confidence is not None else [0.0] * len(tracked),
            tracked.class_id if tracked.class_id is not None else [-1] * len(tracked),
            tracked.tracker_id,
            strict=False,
        ):
            cls_int = int(cls)
            out.append(
                Track(
                    track_id=int(tid),
                    bbox=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                    confidence=float(conf),
                    class_id=cls_int,
                    class_name=VEHICLE_CLASSES.get(cls_int, "vehicle"),
                )
            )
        return out
