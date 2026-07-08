from _shared import JsonHandler, backend


class handler(JsonHandler):
    def do_GET(self):
        payload = backend.build_example_problem(self.query())
        self.send_json(payload, status=200 if payload.get("text") else 503)
