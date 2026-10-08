# Local dev server that tells the browser never to cache, so a refresh always shows the latest build.
# Usage: python3 tools/serve.py [port]
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
ThreadingHTTPServer(('127.0.0.1', port), NoCache).serve_forever()
