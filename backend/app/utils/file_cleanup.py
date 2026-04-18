"""Periodic cleanup of uploads / reports older than the retention window."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from loguru import logger


async def periodic_cleanup(
    paths: list[Path],
    retention_seconds: int,
    interval_seconds: int = 3600,
) -> None:
    """Background coroutine that prunes stale files in *paths*."""
    while True:
        try:
            cutoff = time.time() - retention_seconds
            for root in paths:
                if not root.exists():
                    continue
                for entry in root.iterdir():
                    try:
                        if entry.is_file() and entry.stat().st_mtime < cutoff:
                            entry.unlink(missing_ok=True)
                            logger.info("Cleaned up stale file: {}", entry)
                    except OSError as exc:
                        logger.warning("Failed cleaning {}: {}", entry, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Cleanup loop error: {}", exc)
        await asyncio.sleep(interval_seconds)
