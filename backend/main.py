from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from backend.common import load_config
    from backend.manager import JobManager
else:
    from .common import load_config
    from .manager import JobManager

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
except ImportError as exc:  # pragma: no cover - optional dependency
    raise RuntimeError(
        "FastAPI is not installed. Run `python -m backend.dev_server` for the zero-dependency demo, or install requirements.txt to use this entrypoint."
    ) from exc


CONFIG = load_config()
MANAGER = JobManager(CONFIG)
app = FastAPI(title="Lite Digital Human Demo", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "lite-digital-human-demo"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(CONFIG.web_dir / "index.html")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(CONFIG.web_dir / "app.js")


@app.get("/styles.css")
def styles_css() -> FileResponse:
    return FileResponse(CONFIG.web_dir / "styles.css")


@app.post("/api/speak")
def speak(payload: dict) -> dict:
    text = str(payload.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    record = MANAGER.submit(text)
    return {"job": MANAGER.public_job(record), "message": "queued"}


@app.post("/api/stop")
def stop(payload: dict) -> dict:
    job_id = str(payload.get("job_id", "")).strip() or None
    record = MANAGER.stop(job_id)
    if record is None:
        return {"ok": False, "message": "no active job"}
    return {"ok": True, "job": MANAGER.public_job(record)}


@app.get("/api/metrics")
def metrics() -> dict:
    return MANAGER.metrics().to_dict()


@app.get("/api/jobs")
def jobs(limit: int = 20) -> dict:
    return {"jobs": MANAGER.public_jobs(limit=limit)}


@app.get("/api/status")
def status(job_id: str) -> dict:
    record = MANAGER.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="job not found")
    return MANAGER.public_job(record)


@app.get("/outputs/{job_id}/{filename}")
def outputs(job_id: str, filename: str) -> FileResponse:
    candidate = (CONFIG.outputs_dir / job_id / filename).resolve()
    try:
        candidate.relative_to((CONFIG.outputs_dir / job_id).resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid path")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(candidate)


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("uvicorn is not installed. Run `python -m backend.dev_server` instead.") from exc

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
