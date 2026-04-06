from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .common import AppConfig, PipelineStopped
from .external import ExternalExecutionError, run_command
from .renderer import PreviewRenderer
from .runtime import ModelRegistry


class LipSyncBackend:
    name = "lip-sync"

    def available(self) -> bool:
        return True

    def render(self, job_id: str, audio_path: Path, video_path: Path, stop_event) -> None:
        raise NotImplementedError


class MuseTalkBackend(LipSyncBackend):
    name = "musetalk"

    def __init__(self, config: AppConfig, registry: ModelRegistry) -> None:
        self.config = config
        self.registry = registry

    def _command(self):
        return self.registry.launcher_command(
            "musetalk",
            script_candidates=["inference.py", "infer.py", "demo.py", "app.py"],
        )

    def available(self) -> bool:
        return self._command() is not None

    def render(self, job_id: str, audio_path: Path, video_path: Path, stop_event) -> None:
        command = self._command()
        if command is None:
            raise RuntimeError(
                "MuseTalk backend is not configured. Set DHD_MUSETALK_CMD or place a launcher script under models/MuseTalk."
            )

        video_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "DHD_JOB_ID": job_id,
                "DHD_AUDIO_IN": str(audio_path),
                "DHD_VIDEO_OUT": str(video_path),
                "DHD_MODEL_DIR": str(self.registry.musetalk_dir),
                "DHD_ASSETS_DIR": str(self.registry.assets_dir),
                "DHD_OUTPUTS_DIR": str(self.registry.outputs_dir),
                "DHD_AVATAR_IMAGE": str(self.registry.assets_dir / "avatar.png"),
            }
        )
        run_command(command, stop_event, cwd=self.registry.musetalk_dir, env=env)
        if not video_path.exists():
            raise ExternalExecutionError("MuseTalk command completed but did not create the output mp4 file")


class Wav2LipBackend(LipSyncBackend):
    name = "wav2lip"

    def __init__(self, config: AppConfig, registry: ModelRegistry) -> None:
        self.config = config
        self.registry = registry

    def _command(self):
        return self.registry.launcher_command(
            "wav2lip",
            script_candidates=["inference.py", "infer.py", "demo.py", "app.py"],
        )

    def available(self) -> bool:
        return self._command() is not None

    def render(self, job_id: str, audio_path: Path, video_path: Path, stop_event) -> None:
        command = self._command()
        if command is None:
            raise RuntimeError(
                "Wav2Lip backend is not configured. Set DHD_WAV2LIP_CMD or place a launcher script under models/Wav2Lip."
            )

        video_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "DHD_JOB_ID": job_id,
                "DHD_AUDIO_IN": str(audio_path),
                "DHD_VIDEO_OUT": str(video_path),
                "DHD_MODEL_DIR": str(self.registry.wav2lip_dir),
                "DHD_ASSETS_DIR": str(self.registry.assets_dir),
                "DHD_OUTPUTS_DIR": str(self.registry.outputs_dir),
                "DHD_AVATAR_IMAGE": str(self.registry.assets_dir / "avatar.png"),
            }
        )
        run_command(command, stop_event, cwd=self.registry.wav2lip_dir, env=env)
        if not video_path.exists():
            raise ExternalExecutionError("Wav2Lip command completed but did not create the output mp4 file")


class DemoPreviewBackend(LipSyncBackend):
    name = "demo-preview"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.renderer = PreviewRenderer(config)

    def available(self) -> bool:
        return True

    def render(self, job_id: str, audio_path: Path, video_path: Path, stop_event) -> None:
        self.renderer.render(job_id, audio_path, video_path, stop_event)


class CompositeLipSyncBackend(LipSyncBackend):
    def __init__(self, config: AppConfig, registry: ModelRegistry) -> None:
        self.config = config
        self.registry = registry
        self.last_backend_name = ""
        self.backends = [
            MuseTalkBackend(config, registry),
            Wav2LipBackend(config, registry),
            DemoPreviewBackend(config),
        ]

    @property
    def name(self) -> str:
        return "+".join(backend.name for backend in self.backends)

    def render(self, job_id: str, audio_path: Path, video_path: Path, stop_event) -> None:
        last_error: Optional[Exception] = None
        for backend in self.backends:
            if stop_event.is_set():
                raise PipelineStopped("stopped before render")
            try:
                if backend.available():
                    backend.render(job_id, audio_path, video_path, stop_event)
                    self.last_backend_name = backend.name
                    return
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("no lip sync backend available")