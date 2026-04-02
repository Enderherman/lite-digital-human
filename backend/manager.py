from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from .common import AppConfig, JobRecord, JobStatus, MetricsSnapshot, PipelineStopped, time_iso
from .renderer import PreviewRenderer
from .tts import CompositeSpeechBackend


class JobManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.speech_backend = CompositeSpeechBackend(config)
        self.renderer = PreviewRenderer(config)
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.RLock()
        self._run_lock = threading.Lock()
        self._stop_events: Dict[str, threading.Event] = {}
        self._active_job_id = ""

    def submit(self, text: str) -> JobRecord:
        clean_text = (text or "").strip()
        if not clean_text:
            raise ValueError("text must not be empty")

        job_id = uuid.uuid4().hex[:12]
        now = time.time()
        job_dir = self.config.outputs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        record = JobRecord(
            job_id=job_id,
            text=clean_text,
            status=JobStatus.queued,
            created_at=now,
            updated_at=now,
            output_dir=str(job_dir),
        )
        with self._lock:
            self._jobs[job_id] = record
            self._stop_events[job_id] = threading.Event()
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()
        return record

    def stop(self, job_id: Optional[str] = None) -> Optional[JobRecord]:
        with self._lock:
            target = job_id or self._active_job_id
            stop_event = self._stop_events.get(target)
            if stop_event is not None:
                stop_event.set()
            return self._jobs.get(target)

    def list_jobs(self, limit: int = 20) -> List[JobRecord]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
            return jobs[:limit]

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def latest(self) -> Optional[JobRecord]:
        jobs = self.list_jobs(limit=1)
        return jobs[0] if jobs else None

    def metrics(self) -> MetricsSnapshot:
        with self._lock:
            jobs = list(self._jobs.values())
            queued = sum(1 for job in jobs if job.status == JobStatus.queued)
            running = sum(1 for job in jobs if job.status == JobStatus.running)
            succeeded = sum(1 for job in jobs if job.status == JobStatus.succeeded)
            failed = sum(1 for job in jobs if job.status == JobStatus.failed)
            cancelled = sum(1 for job in jobs if job.status == JobStatus.cancelled)
            completed = [job for job in jobs if job.status in {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}]
            if completed:
                avg_tts = sum(job.tts_ms for job in completed) / len(completed)
                avg_render = sum(job.render_ms for job in completed) / len(completed)
                avg_total = sum(job.total_ms for job in completed) / len(completed)
            else:
                avg_tts = avg_render = avg_total = 0.0
            return MetricsSnapshot(
                queued=queued,
                running=running,
                succeeded=succeeded,
                failed=failed,
                cancelled=cancelled,
                total_jobs=len(jobs),
                average_tts_ms=round(avg_tts, 2),
                average_render_ms=round(avg_render, 2),
                average_total_ms=round(avg_total, 2),
                active_job_id=self._active_job_id,
            )

    def _write_manifest(self, record: JobRecord) -> None:
        manifest_path = Path(record.output_dir) / record.manifest_file
        payload = {
            "job": record.to_dict(),
            "created_at_iso": time_iso(record.created_at),
            "updated_at_iso": time_iso(record.updated_at),
            "backend": record.backend,
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _finalize(self, record: JobRecord) -> None:
        record.updated_at = time.time()
        self._write_manifest(record)

    def _run_job(self, job_id: str) -> None:
        stop_event = self._stop_events[job_id]
        with self._run_lock:
            with self._lock:
                record = self._jobs[job_id]
                record.status = JobStatus.running
                record.started_at = time.time()
                record.updated_at = record.started_at
                record.backend = self.speech_backend.name
                self._active_job_id = job_id
                self._write_manifest(record)

            audio_path = Path(record.output_dir) / record.audio_file
            video_path = Path(record.output_dir) / record.video_file
            total_start = time.perf_counter()

            try:
                tts_start = time.perf_counter()
                self.speech_backend.synthesize(record.text, audio_path, stop_event, self.config)
                record.tts_ms = round((time.perf_counter() - tts_start) * 1000.0, 2)
                if stop_event.is_set():
                    raise PipelineStopped("cancelled after tts")

                render_start = time.perf_counter()
                self.renderer.render(job_id, audio_path, video_path, stop_event)
                record.render_ms = round((time.perf_counter() - render_start) * 1000.0, 2)
                if stop_event.is_set():
                    raise PipelineStopped("cancelled after render")

                record.status = JobStatus.succeeded
                record.audio_file = audio_path.name
                record.video_file = video_path.name
                record.error = ""
            except PipelineStopped as exc:
                record.status = JobStatus.cancelled
                record.error = str(exc)
            except Exception as exc:
                record.status = JobStatus.failed
                record.error = str(exc)
            finally:
                record.finished_at = time.time()
                record.total_ms = round((time.perf_counter() - total_start) * 1000.0, 2)
                self._finalize(record)
                with self._lock:
                    if self._active_job_id == job_id:
                        self._active_job_id = ""
                    self._stop_events.pop(job_id, None)

    def public_job(self, record: JobRecord) -> Dict[str, object]:
        data = record.to_dict()
        data["audio_url"] = "/outputs/%s/%s" % (record.job_id, record.audio_file)
        data["video_url"] = "/outputs/%s/%s" % (record.job_id, record.video_file)
        data["manifest_url"] = "/outputs/%s/%s" % (record.job_id, record.manifest_file)
        return data

    def public_jobs(self, limit: int = 20) -> List[Dict[str, object]]:
        return [self.public_job(job) for job in self.list_jobs(limit=limit)]

    def snapshot(self, job_id: Optional[str] = None) -> Dict[str, object]:
        if job_id:
            record = self.get(job_id)
            if record is None:
                raise KeyError(job_id)
            return self.public_job(record)
        return {
            "metrics": self.metrics().to_dict(),
            "jobs": self.public_jobs(),
        }
