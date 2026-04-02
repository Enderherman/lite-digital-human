from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.common import load_config
from backend.manager import JobManager


DEFAULT_TEXT = "大家好，这里是本地数字人 Demo 的第一版骨架。我们先打通文本、语音和预览链路，再逐步接入 MuseTalk 和 CosyVoice。"


def wait_for_job(manager: JobManager, job_id: str, timeout: float = 120.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = manager.get(job_id)
        if job is None:
            raise RuntimeError("job disappeared")
        if job.status.value in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.5)
    raise TimeoutError("job %s did not finish in time" % job_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default=DEFAULT_TEXT)
    args = parser.parse_args()

    config = load_config()
    manager = JobManager(config)
    record = manager.submit(args.text)
    finished = wait_for_job(manager, record.job_id)
    payload = manager.public_job(finished)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    video_path = Path(finished.output_dir) / finished.video_file
    audio_path = Path(finished.output_dir) / finished.audio_file
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)
    return 0 if finished.status.value == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
