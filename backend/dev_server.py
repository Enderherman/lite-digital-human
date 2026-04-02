from __future__ import annotations

import json
import mimetypes
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional

if __package__ in {None, ""}:
    import sys

    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from backend.common import AppConfig, load_config
    from backend.manager import JobManager
else:
    from .common import AppConfig, load_config
    from .manager import JobManager


CONFIG = load_config()
MANAGER = JobManager(CONFIG)


def _send_json(handler: BaseHTTPRequestHandler, payload: Dict[str, object], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _serve_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    if not path.exists() or not path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return
    content_type, _ = mimetypes.guess_type(str(path))
    content_type = content_type or "application/octet-stream"
    body = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _parse_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    return json.loads(raw.decode("utf-8"))


def _safe_output_path(config: AppConfig, relative: str) -> Optional[Path]:
    candidate = (config.outputs_dir / relative).resolve()
    try:
        candidate.relative_to(config.outputs_dir.resolve())
    except ValueError:
        return None
    return candidate


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "LiteDigitalHuman/0.1"

    def log_message(self, format: str, *args) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in {"/", "/index.html"}:
            _serve_file(self, CONFIG.web_dir / "index.html")
            return
        if path == "/app.js":
            _serve_file(self, CONFIG.web_dir / "app.js")
            return
        if path == "/styles.css":
            _serve_file(self, CONFIG.web_dir / "styles.css")
            return
        if path == "/api/health":
            _send_json(self, {"ok": True, "service": "lite-digital-human-demo"})
            return
        if path == "/api/metrics":
            _send_json(self, MANAGER.metrics().to_dict())
            return
        if path == "/api/jobs":
            query = urllib.parse.parse_qs(parsed.query)
            limit = int(query.get("limit", ["20"])[0])
            _send_json(self, {"jobs": MANAGER.public_jobs(limit=limit)})
            return
        if path == "/api/status":
            query = urllib.parse.parse_qs(parsed.query)
            job_id = query.get("job_id", [""])[0]
            if not job_id:
                _send_json(self, {"error": "job_id is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            record = MANAGER.get(job_id)
            if record is None:
                _send_json(self, {"error": "job not found"}, status=HTTPStatus.NOT_FOUND)
                return
            _send_json(self, MANAGER.public_job(record))
            return
        if path.startswith("/outputs/"):
            rel = path.removeprefix("/outputs/")
            safe = _safe_output_path(CONFIG, rel)
            if safe is None:
                _send_json(self, {"error": "invalid path"}, status=HTTPStatus.BAD_REQUEST)
                return
            _serve_file(self, safe)
            return
        _send_json(self, {"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/speak":
            try:
                payload = _parse_json_body(self)
                text = str(payload.get("text", "")).strip()
                if not text:
                    _send_json(self, {"error": "text is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                record = MANAGER.submit(text)
                _send_json(self, {"job": MANAGER.public_job(record), "message": "queued"}, status=HTTPStatus.ACCEPTED)
            except Exception as exc:
                _send_json(self, {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/stop":
            try:
                payload = _parse_json_body(self)
                job_id = str(payload.get("job_id", "")).strip() or None
                record = MANAGER.stop(job_id)
                if record is None:
                    _send_json(self, {"ok": False, "message": "no active job"})
                    return
                _send_json(self, {"ok": True, "job": MANAGER.public_job(record)})
            except Exception as exc:
                _send_json(self, {"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        _send_json(self, {"error": "not found"}, status=HTTPStatus.NOT_FOUND)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print("Local demo ready: http://%s:%s" % (host, port))
    print("Outputs directory: %s" % CONFIG.outputs_dir)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
