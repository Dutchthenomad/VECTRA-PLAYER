#!/usr/bin/env python3
"""Serve the rug events explorer with local capture auto-loading."""

from __future__ import annotations

import argparse
import json
import mimetypes
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "src" / "rugs_recordings" / "rug_events_explorer.html"
CAPTURES_DIR = ROOT / "src" / "rugs_recordings" / "raw_captures"


class RugExplorerHandler(BaseHTTPRequestHandler):
    server_version = "RugExplorer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            return self._serve_file(HTML_PATH)
        if parsed.path == "/api/manifest":
            return self._serve_manifest()
        if parsed.path == "/api/file":
            return self._serve_capture(parsed.query)
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args) -> None:
        return

    def _serve_manifest(self) -> None:
        if not CAPTURES_DIR.exists():
            self.send_error(404, "Capture directory not found")
            return
        files = sorted(CAPTURES_DIR.glob("*.jsonl"))
        payload = [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            }
            for path in files
        ]
        body = json.dumps({"files": payload}).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8")

    def _serve_capture(self, query: str) -> None:
        qs = parse_qs(query)
        name = qs.get("name", [""])[0]
        if not name:
            self.send_error(400, "Missing name parameter")
            return
        safe_name = Path(unquote(name)).name
        if not safe_name.endswith(".jsonl"):
            self.send_error(400, "Invalid file")
            return
        file_path = CAPTURES_DIR / safe_name
        if not file_path.exists():
            self.send_error(404, "File not found")
            return
        self._serve_file(file_path)

    def _serve_file(self, path: Path) -> None:
        if not path.exists():
            self.send_error(404, "File not found")
            return
        content_type, _ = mimetypes.guess_type(path.name)
        if path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".jsonl":
            content_type = "text/plain; charset=utf-8"
        body = path.read_bytes()
        self._send_bytes(body, content_type or "application/octet-stream")

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the rug events explorer.")
    parser.add_argument("--port", type=int, default=8008, help="Port to bind.")
    args = parser.parse_args()

    if not HTML_PATH.exists():
        raise SystemExit(f"Missing explorer HTML at {HTML_PATH}")

    server = HTTPServer(("127.0.0.1", args.port), RugExplorerHandler)
    print(f"Serving rug explorer at http://127.0.0.1:{args.port}")
    print(f"Captures directory: {CAPTURES_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
