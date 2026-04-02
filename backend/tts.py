from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import threading
from pathlib import Path
from typing import Optional

from .common import AppConfig, PipelineStopped, split_chunks


class SpeechBackend:
    name = "speech"

    def available(self) -> bool:
        return True

    def synthesize(self, text: str, wav_path: Path, stop_event: threading.Event, config: AppConfig) -> None:
        raise NotImplementedError


class WindowsSpeechBackend(SpeechBackend):
    name = "windows-speech"

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def available(self) -> bool:
        return os.name == "nt" and shutil.which(self.config.powershell_path) is not None

    def synthesize(self, text: str, wav_path: Path, stop_event: threading.Event, config: AppConfig) -> None:
        if stop_event.is_set():
            raise PipelineStopped("stopped before tts")

        env = os.environ.copy()
        env["DHD_TTS_TEXT"] = text
        env["DHD_TTS_OUT"] = str(wav_path)
        env["DHD_TTS_RATE"] = str(config.tts_rate)
        script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = $synth.GetInstalledVoices()
    $zh = $voices | Where-Object { $_.VoiceInfo.Culture.Name -like 'zh*' } | Select-Object -First 1
    if ($zh) {
        $synth.SelectVoice($zh.VoiceInfo.Name)
    }
    $synth.Rate = [int]$env:DHD_TTS_RATE
    $synth.SetOutputToWaveFile($env:DHD_TTS_OUT)
    $synth.Speak($env:DHD_TTS_TEXT)
} finally {
    $synth.Dispose()
}
"""
        subprocess.run(
            [config.powershell_path, "-NoProfile", "-Command", script],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )


class SyntheticSpeechBackend(SpeechBackend):
    name = "synthetic-tone"

    def synthesize(self, text: str, wav_path: Path, stop_event: threading.Event, config: AppConfig) -> None:
        if stop_event.is_set():
            raise PipelineStopped("stopped before synthetic tts")

        chunks = split_chunks(text)
        duration = min(config.tts_max_duration_seconds, max(2.4, 1.2 + len(text) * 0.06 + len(chunks) * 0.28))
        sample_rate = config.tts_sample_rate
        frame_count = int(duration * sample_rate)
        chunk_span = max(1, frame_count // max(1, len(chunks)))

        wav_path.parent.mkdir(parents=True, exist_ok=True)
        import wave

        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for frame_index in range(frame_count):
                if stop_event.is_set():
                    raise PipelineStopped("stopped during synthetic tts")
                chunk = chunks[min(len(chunks) - 1, frame_index // chunk_span)]
                base_char = ord(chunk[frame_index % len(chunk)]) if chunk else 65
                base_freq = 130 + (base_char % 36) * 6
                t = frame_index / sample_rate
                envelope = 0.45 + 0.25 * math.sin(2.0 * math.pi * min(2.0, len(chunks) / duration) * t)
                amplitude = envelope * (0.7 if any(ch.isalnum() for ch in chunk) else 0.4)
                sample = (
                    math.sin(2.0 * math.pi * base_freq * t)
                    + 0.45 * math.sin(2.0 * math.pi * base_freq * 2.0 * t)
                    + 0.22 * math.sin(2.0 * math.pi * base_freq * 3.0 * t)
                )
                sample = int(max(-32767, min(32767, sample * amplitude * 12000)))
                wav_file.writeframesraw(struct.pack("<h", sample))


class CompositeSpeechBackend(SpeechBackend):
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.backends = []
        if config.prefer_windows_speech:
            self.backends.append(WindowsSpeechBackend(config))
        self.backends.append(SyntheticSpeechBackend())

    @property
    def name(self) -> str:
        return "+".join(backend.name for backend in self.backends)

    def synthesize(self, text: str, wav_path: Path, stop_event: threading.Event, config: AppConfig) -> None:
        last_error: Optional[Exception] = None
        for backend in self.backends:
            if stop_event.is_set():
                raise PipelineStopped("stopped before tts")
            try:
                if backend.available():
                    backend.synthesize(text, wav_path, stop_event, config)
                    return
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("no speech backend available")
