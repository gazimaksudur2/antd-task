"""Torch device selection for YOLO inference (CUDA vs CPU)."""

from __future__ import annotations

from loguru import logger


def resolve_torch_device(requested: str) -> str:
    """Map *requested* into a device string understood by Ultralytics.

    * ``auto`` — use ``cuda`` if ``torch.cuda.is_available()`` else ``cpu``.
    * ``cpu`` — always CPU.
    * ``cuda`` / ``cuda:0`` / etc. — use that device if CUDA is available; otherwise
      log a warning and fall back to ``cpu``.
    """
    req = (requested or "auto").strip().lower()
    if req == "cpu":
        return "cpu"

    try:
        import torch
    except ImportError:  # pragma: no cover
        logger.warning("PyTorch not installed — using CPU for YOLO")
        return "cpu"

    if req == "auto":
        if torch.cuda.is_available():
            dev = "cuda:0" if torch.cuda.device_count() >= 1 else "cuda"
            return dev
        return "cpu"

    if req.startswith("cuda"):
        if not torch.cuda.is_available():
            logger.warning(
                "YOLO_DEVICE={} requested but torch.cuda.is_available() is False "
                "(install PyTorch **with CUDA**, and NVIDIA drivers) — falling back to CPU",
                requested,
            )
            return "cpu"
        return req

    logger.warning("Unknown YOLO_DEVICE={!r} — using auto", requested)
    return resolve_torch_device("auto")


def log_cuda_diagnostics(device: str) -> None:
    """Emit one-line GPU info when running on CUDA."""
    if not device.startswith("cuda"):
        return
    try:
        import torch

        idx = torch.cuda.current_device() if torch.cuda.is_available() else 0
        name = torch.cuda.get_device_name(idx)
        cap = torch.cuda.get_device_capability(idx)
        logger.info("CUDA device {}: {} (capability {}.{})", idx, name, cap[0], cap[1])
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not read CUDA device name: {}", exc)
