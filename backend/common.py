from __future__ import annotations

import os
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class PipelineStopped(RuntimeError):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def time_iso(ts: Optional[float] = None) -> str:
    value = time.localtime(ts or time.time())
    return time.strftime("%Y-%m-%dT%H:%M:%S", value)


def slugify(text: str, fallback: str = "demo") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug or fallback


def escape_drawtext_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:")


def read_wav_duration(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate or 1)


def split_chunks(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"[\u3002\uff01\uff1f!?;\uff1b,\n]+", text) if chunk.strip()]
    return chunks or [text.strip() or "Hello from the local demo."]


def find_first_existing(paths: list[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


@dataclass
class AppConfig:
    root_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1])
    outputs_dir: Path = field(init=False)
    web_dir: Path = field(init=False)
    preview_width: int = 720
    preview_height: int = 1280
    preview_fps: int = 25
    tts_sample_rate: int = 22050
    tts_max_duration_seconds: int = 18
    tts_rate: int = 0
    prefer_windows_speech: bool = True
    ffmpeg_path: str = "ffmpeg"
    powershell_path: str = "powershell"

    def __post_init__(self) -> None:
        self.outputs_dir = self.root_dir / "outputs"
        self.web_dir = self.root_dir / "web"

    def apply_env(self) -> "AppConfig":
        self.root_dir = Path(os.getenv("DHD_ROOT_DIR", str(self.root_dir))).resolve()
        self.outputs_dir = Path(os.getenv("DHD_OUTPUTS_DIR", str(self.root_dir / "outputs"))).resolve()
        self.web_dir = Path(os.getenv("DHD_WEB_DIR", str(self.root_dir / "web"))).resolve()
        self.preview_width = _env_int("DHD_PREVIEW_WIDTH", self.preview_width)
        self.preview_height = _env_int("DHD_PREVIEW_HEIGHT", self.preview_height)
        self.preview_fps = _env_int("DHD_PREVIEW_FPS", self.preview_fps)
        self.tts_sample_rate = _env_int("DHD_TTS_SAMPLE_RATE", self.tts_sample_rate)
        self.tts_max_duration_seconds = _env_int("DHD_TTS_MAX_DURATION_SECONDS", self.tts_max_duration_seconds)
        self.tts_rate = _env_int("DHD_TTS_RATE", self.tts_rate)
        self.prefer_windows_speech = _env_bool("DHD_PREFER_WINDOWS_SPEECH", self.prefer_windows_speech)
        self.ffmpeg_path = os.getenv("DHD_FFMPEG", self.ffmpeg_path)
        self.powershell_path = os.getenv("DHD_POWERSHELL", self.powershell_path)
        return self

    def ensure_dirs(self) -> None:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.web_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    config = AppConfig().apply_env()
    config.ensure_dirs()
    return config


@dataclass
class JobRecord:
    job_id: str
    text: str
    status: JobStatus
    created_at: float
    updated_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    output_dir: str = ""
    audio_file: str = "speech.wav"
    video_file: str = "preview.mp4"
    manifest_file: str = "manifest.json"
    backend: str = ""
    error: str = ""
    tts_ms: float = 0.0
    render_ms: float = 0.0
    total_ms: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at_iso"] = time_iso(self.created_at)
        data["updated_at_iso"] = time_iso(self.updated_at)
        data["started_at_iso"] = time_iso(self.started_at) if self.started_at else ""
        data["finished_at_iso"] = time_iso(self.finished_at) if self.finished_at else ""
        return data


@dataclass
class MetricsSnapshot:
    queued: int
    running: int
    succeeded: int
    failed: int
    cancelled: int
    total_jobs: int
    average_tts_ms: float
    average_render_ms: float
    average_total_ms: float
    active_job_id: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
