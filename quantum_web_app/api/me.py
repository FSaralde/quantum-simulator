from _shared import JsonHandler


class handler(JsonHandler):
    def do_GET(self):
        self.send_json({"user": None})
