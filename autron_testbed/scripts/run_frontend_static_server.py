from __future__ import annotations

import http.client
import http.server
import os
import socketserver
import sys
import urllib.parse
from pathlib import Path

DIST_DIR = Path(sys.argv[1]).resolve()
HOST = sys.argv[2]
PORT = int(sys.argv[3])
API_TARGET = sys.argv[4]

parsed_target = urllib.parse.urlparse(API_TARGET)
TARGET_HOST = parsed_target.hostname or "127.0.0.1"
TARGET_PORT = parsed_target.port or 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy("GET")
            return
        if self.path.startswith("/assets/") or self.path in ("/", "/index.html"):
            return super().do_GET()
        if "." not in self.path.rsplit("/", 1)[-1]:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
            return
        self.send_error(405)

    def _proxy(self, method: str) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        conn = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT, timeout=30)
        headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
        conn.request(method, self.path.removeprefix("/api"), body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        self.send_response(resp.status)
        for key, value in resp.getheaders():
            if key.lower() in {"transfer-encoding", "connection", "date", "server"}:
                continue
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)
        conn.close()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


with ReusableTCPServer((HOST, PORT), Handler) as httpd:
    print(f"Serving {DIST_DIR} on http://{HOST}:{PORT}")
    print(f"Proxying /api to {API_TARGET}")
    httpd.serve_forever()
