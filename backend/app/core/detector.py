"""YOLOv8 wrapper restricted to COCO vehicle classes."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
from loguru import logger

# COCO class IDs for the vehicle types we care about.
VEHICLE_CLASSES: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


@dataclass(slots=True)
class Detection:
    """A single per-frame detection prior to tracking."""

    bbox: tuple[float, float, float, float]  # xyxy in resized-frame coords
    confidence: float
    class_id: int
    class_name: str


class YoloDetector:
    """Thread-safe-ish singleton wrapper around an Ultralytics YOLO model.

    The model itself is not re-entrant for inference, so we serialise calls
    with a lock. For a PoC with one worker thread per job that is fine and
    avoids the cost of loading the weights more than once.
    """

    _instance: "YoloDetector | None" = None
    _instance_lock = threading.Lock()

    def __init__(self, weights: str, conf_threshold: float) -> None:
        from ultralytics import YOLO  # heavy import — keep inside

        logger.info("Loading YOLO weights '{}'", weights)
        self._model = YOLO(weights)
        self._conf = conf_threshold
        self._infer_lock = threading.Lock()
        try:
            import torch

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            if self._device == "cuda":
                self._model.to(self._device)
                logger.info("YOLO running on CUDA")
            else:
                logger.info("YOLO running on CPU")
        except Exception:  # pragma: no cover - torch is a hard dep but defensive
            self._device = "cpu"

    @classmethod
    def get(cls, weights: str, conf_threshold: float) -> "YoloDetector":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(weights=weights, conf_threshold=conf_threshold)
            return cls._instance

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        """Run inference on a single BGR frame and return vehicle detections."""
        with self._infer_lock:
            results = self._model.predict(
                source=frame_bgr,
                conf=self._conf,
                classes=list(VEHICLE_CLASSES.keys()),
                verbose=False,
                device=self._device,
            )
        if not results:
            return []
        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []

        xyxy = result.boxes.xyxy.cpu().numpy()
        conf = result.boxes.conf.cpu().numpy()
        cls = result.boxes.cls.cpu().numpy().astype(int)

        detections: list[Detection] = []
        for box, c, k in zip(xyxy, conf, cls, strict=False):
            if int(k) not in VEHICLE_CLASSES:
                continue
            x1, y1, x2, y2 = (float(v) for v in box)
            detections.append(
                Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=float(c),
                    class_id=int(k),
                    class_name=VEHICLE_CLASSES[int(k)],
                )
            )
        return detections
