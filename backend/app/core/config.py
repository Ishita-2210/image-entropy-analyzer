"""Validated startup configuration. All limits apply before expensive processing."""

import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field


def configure_logging():
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            message = record.getMessage()
            try:
                payload = json.loads(message)
            except (ValueError, TypeError):
                payload = {"event": message}
            if not isinstance(payload, dict):
                payload = {"event": message}
            payload["level"] = record.levelname
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload)

    logger = logging.getLogger("iea")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class Settings(BaseModel):
    max_upload_mb: int = Field(default=24, ge=1, le=100)
    max_pixels: int = Field(default=16_000_000, ge=1024, le=64_000_000)
    max_analysis_pixels: int = Field(default=4_000_000, ge=1024, le=16_000_000)
    store_mb: int = Field(default=192, ge=32, le=2048)
    workers: int = Field(default=2, ge=1, le=4)
    max_jobs: int = Field(default=10, ge=1, le=32)
    job_seconds: int = Field(default=120, ge=5, le=600)
    history: bool = False
    history_path: Path = Path(".runtime/history.sqlite3")
    origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]

    @classmethod
    def from_env(cls):
        values = {}
        for key in cls.model_fields:
            value = os.getenv(f"IEA_{key.upper()}")
            if value is not None:
                values[key] = value.split(",") if key in ("origins", "hosts") else value
        return cls(**values)
