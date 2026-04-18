"""File-upload validation helpers."""

from __future__ import annotations

from pathlib import Path

import filetype

ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
}

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


class InvalidVideoFile(ValueError):
    """Raised when an uploaded file is not a recognised video container."""


def validate_video_bytes(head_bytes: bytes, filename: str) -> str:
    """Verify magic bytes match a known video container.

    Returns the detected MIME type. Raises :class:`InvalidVideoFile` on
    failure. We require ``head_bytes`` to contain at least the first 261
    bytes of the file (filetype's recommended minimum).
    """
    suffix = Path(filename).suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise InvalidVideoFile(f"Unsupported file extension: {suffix}")

    kind = filetype.guess(head_bytes)
    if kind is None:
        raise InvalidVideoFile("Could not detect file type from contents")
    if kind.mime not in ALLOWED_VIDEO_MIMES:
        raise InvalidVideoFile(
            f"Unsupported video format '{kind.mime}'. Allowed: "
            + ", ".join(sorted(ALLOWED_VIDEO_MIMES))
        )
    return kind.mime
