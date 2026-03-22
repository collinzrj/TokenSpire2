"""HTTP server and background loop."""

import json
import os
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .config import find_latest_history
from .html_template import VIEWER_HTML


class ViewerHandler(SimpleHTTPRequestHandler):
    json_path = None
    watch_dir = None
    state = None  # EnrichedState
    tts = None    # AliyunTTS

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            self._respond(200, "text/html", VIEWER_HTML.encode("utf-8"))
        elif p == "/api/state":
            enriched = self.state.get_enriched_path()
            try:
                if enriched and os.path.isfile(enriched):
                    with open(enriched, "r", encoding="utf-8") as f:
                        data = f.read().encode("utf-8")
                else:
                    data = b"[]"
            except (FileNotFoundError, PermissionError):
                data = b"[]"
            self._respond(200, "application/json", data, no_cache=True)
        elif p == "/api/tts":
            params = parse_qs(urlparse(self.path).query)
            text = params.get("text", [""])[0]
            if not text or not self.tts:
                self._respond(400, "text/plain", b"No text or TTS not configured")
                return
            print(f"[TTS] {text[:50]}...")
            wav = self.tts.synthesize(text)
            if wav:
                self._respond(200, "audio/wav", wav, no_cache=True)
            else:
                self._respond(500, "text/plain", b"TTS failed")
        else:
            self.send_error(404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/comment":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                data = json.loads(body)
                comments = data.get("comments", [])
            except json.JSONDecodeError:
                comments = [body.strip()] if body.strip() else []
            if comments and self.watch_dir:
                instruction_path = os.path.join(self.watch_dir, "instruction.txt")
                text = "\n".join(f"[观众] {c}" for c in comments)
                try:
                    with open(instruction_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"[Comment] {len(comments)} comments -> instruction.txt")
                except Exception as e:
                    print(f"[Comment] Write error: {e}")
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, code, ctype, data, no_cache=False):
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        if no_cache:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def background_loop(state, handler_cls):
    """Polls file + summarizes every 3 seconds."""
    while True:
        time.sleep(3)
        try:
            path = handler_cls.json_path
            if handler_cls.watch_dir:
                latest = find_latest_history(handler_cls.watch_dir)
                if latest:
                    if path != latest:
                        handler_cls.json_path = latest
                        print(f"Now watching: {latest}")
                    path = latest
            state.update_from_file(path)
            state.summarize_pending()
        except Exception as e:
            print(f"[Background] Error: {e}")
