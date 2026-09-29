from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from tts import available, synthesize, utterance
from dialogue import reply, configuration, LEARNER_LANGUAGES

PUBLIC = Path(__file__).resolve().parent / "public"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".webp": "image/webp",
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            body = json.dumps({"ok": True, "service": "talema-avatar", "tts": available(), "dialogue": configuration(),
                               "input_languages": list(LEARNER_LANGUAGES)}).encode()
            self._send(200, body, "application/json")
            return
        asset = (PUBLIC / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
        if asset.is_file() and PUBLIC in asset.parents:
            self._send(200, asset.read_bytes(), CONTENT_TYPES.get(asset.suffix, "text/javascript; charset=utf-8"))
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/respond", "/api/audio", "/api/utterance"}:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("Request body too large or empty")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            talema = str(payload.get("talema", ""))
            if len(talema) > 2000:
                raise ValueError("Message too long")
            if not talema.strip() and not (path == "/api/respond" and payload.get("start") is True):
                raise ValueError("talema is required")
            if path == "/api/utterance":
                self._send(200, json.dumps(utterance(talema)).encode(), "application/json")
                return
            if path == "/api/audio":
                audio, provider, phonemes = synthesize(talema, payload.get("provider"))
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(audio)))
                self.send_header("X-Talema-TTS", provider)
                self.end_headers()
                self.wfile.write(audio)
                return
            # `talema` is the learner's message: Talema by default, English when `language` is "english".
            language = payload.get("language", "talema")
            body = json.dumps(reply(talema, payload.get("history", []), payload.get("start") is True, language),
                              ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except (ValueError, json.JSONDecodeError, RuntimeError, ImportError) as exc:
            self._send(400, json.dumps({"error": str(exc)}).encode(), "application/json")

    def log_message(self, *_args) -> None:
        return

if __name__ == "__main__":
    host = os.getenv("TALEMA_HOST", "127.0.0.1")
    port = int(os.getenv("TALEMA_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Talema avatar: http://{host}:{port}")
    print(f"Tutor configured: {configuration()['configured']} ({configuration()['model'] or 'no model'}); TTS providers: {available()}")
    server.serve_forever()
