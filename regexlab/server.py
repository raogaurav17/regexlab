"""Tiny local web server (standard library only) for the interactive demo."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .api import build_payload, run_payload

WEB = Path(__file__).parent / "web"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload):
        self._send(200, json.dumps(payload).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
        if url.path == "/api/build":
            return self._json(build_payload(qs.get("re", "")))
        if url.path == "/api/run":
            return self._json(run_payload(qs.get("re", ""), qs.get("s", "")))
        name = "index.html" if url.path in ("/", "") else url.path.lstrip("/")
        target = (WEB / name).resolve()
        if WEB.resolve() in target.parents and target.is_file():
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            return self._send(200, target.read_bytes(), ctype)
        self._send(404, b"Not found", "text/plain")

    def log_message(self, *args):      # keep the terminal quiet
        pass


def serve(port: int = 8000, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)   # localhost only
    url = f"http://127.0.0.1:{port}/"
    print(f"regexlab running at {url}  (Ctrl+C to stop)")
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
