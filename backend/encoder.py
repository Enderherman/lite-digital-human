from __future__ import annotations

import threading
from pathlib import Path

from .common import AppConfig, PipelineStopped
from .external import run_command


class VideoEncoder:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def encode(self, source_video: Path, audio_path: Path, output_video: Path, stop_event: threading.Event) -> None:
        if stop_event.is_set():
            raise PipelineStopped("stopped before encode")

        output_video.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.config.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_video),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_video),
        ]
        run_command(command, stop_event)
        if not output_video.exists():
            raise RuntimeError("ffmpeg completed but did not create the final preview video")