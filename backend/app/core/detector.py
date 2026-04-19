"""YOLOv8 wrapper restricted to COCO vehicle classes."""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
from loguru import logger

from app.core.device import log_cuda_diagnostics, resolve_torch_device

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

    _instance: YoloDetector | None = None
    _instance_lock = threading.Lock()
    _instance_key: tuple[str, float, str, bool] | None = None

    def __init__(
        self,
        weights: str,
        conf_threshold: float,
        device: str,
        half: bool = False,
    ) -> None:
        from ultralytics import YOLO  # heavy import — keep inside

        logger.info("Loading YOLO weights '{}'", weights)
        self._model = YOLO(weights)
        self._conf = conf_threshold
        self._infer_lock = threading.Lock()
        self._device = device
        self._half = bool(half) and device.startswith("cuda")

        try:
            self._model.to(self._device)
            if self._device.startswith("cuda"):
                log_cuda_diagnostics(self._device)
                logger.info("YOLO inference device: {} (half_precision={})", self._device, self._half)
            else:
                logger.info("YOLO inference device: cpu (install PyTorch+CUDA to use your RTX GPU)")
        except Exception as exc:  # pragma: no cover
            logger.warning("YOLO .to({}) failed ({}); staying on default device", self._device, exc)
            self._device = "cpu"
            self._half = False

    @classmethod
    def get(
        cls,
        weights: str,
        conf_threshold: float,
        *,
        device: str = "auto",
        half: bool = False,
    ) -> YoloDetector:
        resolved = resolve_torch_device(device)
        key = (weights, conf_threshold, resolved, bool(half) and resolved.startswith("cuda"))
        with cls._instance_lock:
            if cls._instance is not None and cls._instance_key != key:
                logger.info("YOLO config changed — reloading model")
                cls._instance = None
            if cls._instance is None:
                cls._instance = cls(weights, conf_threshold, resolved, key[3])
                cls._instance_key = key
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
                half=self._half,
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
