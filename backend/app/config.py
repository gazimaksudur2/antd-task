"""Application configuration loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, type-checked runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- HTTP server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Storage ---
    data_dir: Path = Path("./data")
    upload_dir: Path = Path("./data/uploads")
    report_dir: Path = Path("./data/reports")

    # --- Upload limits ---
    max_upload_bytes: int = 500 * 1024 * 1024  # 500 MB

    # --- CV pipeline ---
    yolo_model: str = "yolov8n.pt"
    frame_skip: int = Field(default=2, ge=1)
    resize_max: int = Field(default=640, ge=160)
    conf_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    track_buffer: int = Field(default=30, ge=1)
    frame_stream_every: int = Field(default=5, ge=1)

    # --- Retention ---
    file_retention_hours: int = 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
