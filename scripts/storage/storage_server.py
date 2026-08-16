#!/usr/bin/env python3
"""Minimal local content-addressed storage for FL-on-chain debugging.

APIs:
  POST /files          upload raw bytes -> {"id": sha256, "size": n, "url": ...}
  GET  /files          list stored ids
  GET  /files/<id>     download the file (404 if missing)
  GET  /health         {"status": "ok"}

Files are stored by their sha256 hex id under STORAGE_DIR (default
``data/storage``), so identical content dedupes automatically. Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HOST = os.environ.get("STORAGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("STORAGE_PORT", "9000"))
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", "data/storage"))
ID_RE = re.compile(r"^[0-9a-f]{64}$")

_lock = threading.Lock()


def _daemonize(pid_file: Path) -> None:
    """Detach into a new session (setsid + double fork) so the server survives
    the launching shell/terminal being torn down."""
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    with open(os.devnull, "rb") as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())
    pid_file.write_text(str(os.getpid()))


class Handler(BaseHTTPRequestHandler):
    server_version = "FLStorage/0.1"

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/health":
            return self._json(200, {"status": "ok"})
        if path == "/files":
            with _lock:
                ids = sorted(p.name for p in STORAGE_DIR.iterdir() if ID_RE.match(p.name))
            return self._json(200, {"count": len(ids), "ids": ids})
        if path.startswith("/files/"):
            cid = path[len("/files/"):]
            if not ID_RE.match(cid):
                return self._json(400, {"error": "invalid id"})
            target = STORAGE_DIR / cid
            if not target.is_file():
                return self._json(404, {"error": "not found", "id": cid})
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._json(404, {"error": "not found", "path": path})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path != "/files":
            return self._json(404, {"error": "not found", "path": path})
        length = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(length)
        digest = hashlib.sha256(data).hexdigest()
        target = STORAGE_DIR / digest
        if not target.exists():
            with _lock:
                fd, tmp = tempfile.mkstemp(dir=str(STORAGE_DIR), prefix=".upload-")
                try:
                    with os.fdopen(fd, "wb") as f:
                        f.write(data)
                    os.replace(tmp, target)
                except BaseException:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                    raise
        return self._json(201, {"id": digest, "size": len(data), "url": f"/files/{digest}"})

    def log_message(self, fmt: str, *args: object) -> None:
        pass  # 安静运行；日志由 storage.sh 重定向到 data/storage/server.log


def main() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    pid_file = os.environ.get("STORAGE_PID_FILE")
    if pid_file:
        _daemonize(Path(pid_file))
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"storage listening on http://{HOST}:{PORT} (dir={STORAGE_DIR})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
