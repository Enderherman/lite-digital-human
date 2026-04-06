from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from .common import PipelineStopped


class ExternalExecutionError(RuntimeError):
    pass


def run_command(
    command: Sequence[str],
    stop_event: threading.Event,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    poll_interval: float = 0.2,
) -> None:
    proc = subprocess.Popen(
        list(command),
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        while True:
            if stop_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise PipelineStopped("pipeline stopped by user")
            if proc.poll() is not None:
                break
            time.sleep(poll_interval)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            message = (stderr or stdout or "external model command failed").strip()
            raise ExternalExecutionError(message)
    finally:
        if proc.poll() is None:
            proc.kill()