#!/usr/bin/env python3

from functools import partial
import http.server
import json
import os
import socketserver
import urllib.parse

class CallbackRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        if parts.path.strip('/') != 'callback':
            return super().do_GET()

        params = urllib.parse.parse_qs(parts.query)
        if 'a' not in params:
            resp = 'Parameter a must be passed!'
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", 'text/plain')
            self.send_header("Content-Length", len(resp))
            self.end_headers()
            self.wfile.write(resp)
            return

        status = HTTPStatus.OK
        resp = {}

        if params['a'] == 'blah':
            pass
        else:
            resp['error'] = 'unknown value for parameter a'

        rstr = json.dumps(resp)
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(rstr))
        self.end_headers()
        self.wfile.write(rstr)

def start_server():
	d = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/')
	handle = partial(CallbackRequestHandler, directory=d)
	with socketserver.TCPServer(('', 3000), handle) as httpd:
		httpd.serve_forever()

if __name__ == '__main__':
	start_server()
