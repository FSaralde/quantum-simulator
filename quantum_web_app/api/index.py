import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from ._shared import JsonHandler, backend
except ImportError:
    from _shared import JsonHandler, backend

ROOT = Path(__file__).resolve().parents[1]


class handler(JsonHandler):
    def is_api_request(self):
        path = urlparse(self.path).path
        return path == "/api" or path.startswith("/api/")

    def route_name(self):
        path = urlparse(self.path).path.rstrip("/")
        if path.endswith("/api/index.py"):
            return "health"
        if path.startswith("/api/"):
            path = path[len("/api/") :]
        return path.split("/")[-1] or "health"

    def send_static(self):
        raw_path = unquote(urlparse(self.path).path)
        if raw_path in ("", "/"):
            raw_path = "/index.html"

        requested = (ROOT / raw_path.lstrip("/")).resolve()
        if not str(requested).startswith(str(ROOT)) or requested.is_dir():
            requested = ROOT / "index.html"
        if not requested.exists():
            requested = ROOT / "index.html"

        content_type = mimetypes.guess_type(str(requested))[0] or "application/octet-stream"
        body = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.is_api_request():
            self.send_static()
            return

        route = self.route_name()
        query = self.query()

        if route == "health":
            self.send_json({"ok": True})
        elif route == "explain":
            self.send_json(backend.build_explanation(query))
        elif route == "problem":
            payload = backend.build_example_problem(query)
            self.send_json(payload, status=200 if payload.get("text") else 503)
        elif route == "visual":
            payload = backend.build_visual(query)
            self.send_json(payload, status=200 if payload.get("svg") else 503)
        elif route == "double-slit":
            self.send_json(backend.build_double_slit_payload(query))
        elif route == "experiments":
            self.send_json({"experiments": backend.EXPERIMENTS})
        elif route == "me":
            self.send_json({"user": None})
        elif route == "chat":
            self.send_json({"error": "Use POST for /api/chat."}, status=405)
        else:
            self.send_json({"error": f"Unknown API route: {route}"}, status=404)

    def do_POST(self):
        if not self.is_api_request():
            self.send_json({"error": "POST is only supported for API routes."}, status=405)
            return

        route = self.route_name()

        if route != "chat":
            self.send_json({"error": f"POST is not supported for /api/{route}."}, status=405)
            return

        payload = self.read_json()
        if payload is None:
            self.send_json({"error": "Invalid JSON body"}, status=400)
            return
        self.send_json(backend.build_chat_response(payload))
