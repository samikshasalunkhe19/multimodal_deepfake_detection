"""Central configuration: limits, thresholds and paths.

Every value has a safe default and can be overridden with an environment
variable, so nothing is hard-coded deep inside the modules.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}")


def _env_optional_int(name: str) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}")


@dataclass(frozen=True)
class Settings:
    # ---- paths ----
    base_dir: Path = BASE_DIR
    temp_dir: Path = BASE_DIR / "tmp_uploads"
    reports_dir: Path = BASE_DIR / "reports"
    models_dir: Path = BASE_DIR / "models"
    logs_dir: Path = BASE_DIR / "logs"

    # ---- database (swap to postgresql+psycopg2://user:pw@host/db later) ----
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./deepfake_platform.db")

    # ---- upload limits ----
    max_image_bytes: int = _env_int("MAX_IMAGE_MB", 10) * 1024 * 1024
    max_video_bytes: int = _env_int("MAX_VIDEO_MB", 100) * 1024 * 1024
    # Guards against "decompression bombs": tiny files that expand to huge images.
    max_image_pixels: int = _env_int("MAX_IMAGE_PIXELS", 50_000_000)
    temp_file_max_age_seconds: int = 3600

    # ---- image model (Hugging Face Hub id; the first use downloads the weights) ----
    default_image_model_id: str = "dima806/deepfake_vs_real_image_detection"
    image_model_id: str = os.getenv("IMAGE_MODEL_ID", "dima806/deepfake_vs_real_image_detection")
    # Only needed if the model's labels are unclear (e.g. LABEL_0 / LABEL_1).
    fake_label_index: Optional[int] = _env_optional_int("FAKE_LABEL_INDEX")
    # Error Level Analysis is skipped for very large images (memory / time).
    ela_max_pixels: int = 16_000_000

    # ---- video analysis ----
    video_max_seconds: int = _env_int("MAX_VIDEO_SECONDS", 300)   # longer videos are rejected
    video_max_side_px: int = 4096                                  # width or height above this is rejected
    video_sample_fps: float = 1.0                                  # frames analysed per second of video
    video_max_frames: int = _env_int("MAX_VIDEO_FRAMES", 60)       # hard cap, spread evenly over the video

    # ---- fusion (documented priors, see modules/fusion/engine.py) ----
    fusion_weight_image: float = 1.0
    fusion_weight_video: float = 1.2

    # ---- allowed types ----
    image_extensions: tuple = (".jpg", ".jpeg", ".png")
    video_extensions: tuple = (".mp4", ".avi", ".mov")

    # ---- risk categories (tunable; used by the fusion engine) ----
    risk_low_max: float = 35.0    # score <  35  -> Low
    risk_high_min: float = 65.0   # score >  65  -> High, otherwise Medium

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def max_bytes_for(self, kind: str) -> int:
        if kind == "image":
            return self.max_image_bytes
        if kind == "video":
            return self.max_video_bytes
        raise ValueError(f"Unknown file kind: {kind!r}")

    def extensions_for(self, kind: str) -> tuple:
        if kind == "image":
            return self.image_extensions
        if kind == "video":
            return self.video_extensions
        raise ValueError(f"Unknown file kind: {kind!r}")


settings = Settings()


def ensure_directories() -> None:
    """Create the runtime folders. Called once when the backend starts."""
    for d in (settings.temp_dir, settings.reports_dir, settings.models_dir, settings.logs_dir):
        d.mkdir(parents=True, exist_ok=True)
