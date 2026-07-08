from _shared import JsonHandler, backend


class handler(JsonHandler):
    def do_POST(self):
        payload = self.read_json()
        if payload is None:
            self.send_json({"error": "Invalid JSON body"}, status=400)
            return
        self.send_json(backend.build_chat_response(payload))

    def do_GET(self):
        self.send_json({"error": "Use POST for /api/chat."}, status=405)
