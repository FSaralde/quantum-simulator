from _shared import JsonHandler, backend


class handler(JsonHandler):
    def do_GET(self):
        self.send_json(backend.build_explanation(self.query()))
