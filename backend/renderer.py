from __future__ import annotations

import subprocess
import time
import threading
from pathlib import Path

from .common import AppConfig, PipelineStopped, escape_drawtext_path, find_first_existing, read_wav_duration


class PreviewRenderer:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _font_candidates(self):
        windows_fonts = Path("C:/Windows/Fonts")
        return [
            windows_fonts / "msyh.ttc",
            windows_fonts / "msyhbd.ttc",
            windows_fonts / "simhei.ttf",
            windows_fonts / "arialbd.ttf",
            windows_fonts / "arial.ttf",
        ]

    def _choose_font(self) -> Path:
        font = find_first_existing(self._font_candidates())
        if font is None:
            raise RuntimeError("No usable font found under C:/Windows/Fonts for preview rendering.")
        return font

    def _build_filter(self, job_id: str, font_path: Path) -> str:
        font = escape_drawtext_path(font_path)
        label = "LOCAL DIGITAL HUMAN LAB"
        subtitle = "Text -> TTS -> preview mp4"
        footer = "Job %s" % job_id
        stage = "Stage 1 placeholder for MuseTalk / CosyVoice"
        parts = [
            "drawbox=x=48:y=80:w=624:h=1120:color=0f172a@0.88:t=fill",
            "drawbox=x=110:y=150:w=500:h=530:color=1f2937@0.96:t=fill",
            "drawbox=x=150:y=210:w=420:h=420:color=334155@0.40:t=fill",
            "drawbox=x=215:y=300:w=70:h=70:color=e2e8f0@1.0:t=fill",
            "drawbox=x=435:y=300:w=70:h=70:color=e2e8f0@1.0:t=fill",
            "drawbox=x=305:y=435:w=130:h=20:color=fb7185@1.0:t=fill:enable='lt(mod(t\\,0.55)\\,0.27)'",
            "drawbox=x=305:y=446:w=130:h=8:color=fb7185@1.0:t=fill:enable='gte(mod(t\\,0.55)\\,0.27)'",
            "drawtext=fontfile='%s':text='%s':x=(w-text_w)/2:y=785:fontcolor=ffffff:fontsize=42:shadowcolor=000000@0.35:shadowx=2:shadowy=2" % (font, label),
            "drawtext=fontfile='%s':text='%s':x=(w-text_w)/2:y=845:fontcolor=cbd5e1:fontsize=24" % (font, subtitle),
            "drawtext=fontfile='%s':text='%s':x=(w-text_w)/2:y=900:fontcolor=94a3b8:fontsize=22" % (font, footer),
            "drawtext=fontfile='%s':text='%s':x=(w-text_w)/2:y=960:fontcolor=94a3b8:fontsize=20" % (font, stage),
            "format=yuv420p[v]",
        ]
        return ",".join(parts)

    def render(self, job_id: str, audio_path: Path, video_path: Path, stop_event: threading.Event) -> None:
        if stop_event.is_set():
            raise PipelineStopped("stopped before render")

        duration = max(read_wav_duration(audio_path), 2.5)
        font_path = self._choose_font()
        filter_complex = self._build_filter(job_id, font_path)
        video_path.parent.mkdir(parents=True, exist_ok=True)
        input_bg = "color=c=0b1020:s=%dx%d:r=%d:d=%.2f" % (
            self.config.preview_width,
            self.config.preview_height,
            self.config.preview_fps,
            duration,
        )
        cmd = [
            self.config.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            input_bg,
            "-i",
            str(audio_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
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
            str(video_path),
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            while True:
                if stop_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise PipelineStopped("stopped during render")
                if proc.poll() is not None:
                    break
                time.sleep(0.2)
            _, stderr = proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError((stderr or "ffmpeg failed to render preview").strip())
        finally:
            if proc.poll() is None:
                proc.kill()
