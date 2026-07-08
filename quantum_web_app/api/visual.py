from _shared import JsonHandler, backend


class handler(JsonHandler):
    def do_GET(self):
        payload = backend.build_visual(self.query())
        self.send_json(payload, status=200 if payload.get("svg") else 503)
