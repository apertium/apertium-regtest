#!/usr/bin/env python3

from functools import partial
from http import HTTPStatus
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
        else:
            params = urllib.parse.parse_qs(parts.query)
            self.do_callback(params)

    def do_POST(self):
        ln = int(self.headers['Content-Length'])
        data = self.rfile.read(ln)
        self.do_callback(urllib.parse.parse_qs(data.decode('utf-8')))

    def do_callback(self, params):
        print(params)
        if 'a' not in params:
            resp = 'Parameter a must be passed!'
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", 'text/plain')
            self.send_header("Content-Length", len(resp))
            self.end_headers()
            self.wfile.write(resp.encode('utf-8'))
            return

        status = HTTPStatus.OK
        resp = {}

        if params['a'][0] == 'init':
            resp['folder'] = 'nowhere'
            resp['corpora'] = ['blah', 'bloop', 'blarg']
        elif params['a'][0] == 'load':
            try:
                resp = cb_load(params['p'][0])
            except:
                resp['error'] = 'Current state is missing or invalid. You will need to run the regression test for all corpora.'
        elif params['a'][0] == 'run':
            good, out = test_run(params.get('c', ['*'])[0])
            resp['good'] = good
            resp['output'] = output
        else:
            resp['error'] = 'unknown value for parameter a'

        rstr = json.dumps(resp).encode('utf-8')
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
