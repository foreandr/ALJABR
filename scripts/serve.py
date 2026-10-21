"""Serve the local mathematics atlas without loading the entire graph in a browser."""
import argparse
from contextlib import closing
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import webbrowser
from urllib.parse import parse_qs, urlsplit

from atlas_index import neighborhood, search

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in ('/', '/aljabr.html'):
            # Keep the user's reference HTML untouched. Only connect its data
            # adapter while serving the complete disk-backed atlas.
            html = (ROOT/'aljabr.html').read_text(encoding='utf8')
            html = html.replace("(()=>{'use strict';const d=", "(()=>{'use strict';if(window.ALJABR_DATA?.api)return;const d=")
            html = html.replace('</body>', '<script src="atlas-client.js"></script></body>')
            payload = html.encode('utf8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if not url.path.startswith('/api/'):
            if url.path not in ('/', '/aljabr.html', '/aljabr-data.js', '/atlas-client.js', '/favicon.ico'):
                self.send_error(404)
                return
            return super().do_GET()
        query = parse_qs(url.query)
        with closing(sqlite3.connect((ROOT/'aljabr-data.sqlite').as_uri() + '?mode=ro', uri=True)) as database:
            if url.path == '/api/health':
                result = {'app': 'ALJABR', 'metadata': json.loads(database.execute('SELECT payload FROM metadata').fetchone()[0])}
            elif url.path == '/api/search':
                result = search(database, query.get('q', [''])[0], query.get('type', [''])[0])
            elif url.path == '/api/node':
                result = neighborhood(database, query.get('id', [''])[0])
            else:
                self.send_error(404)
                return
        payload = json.dumps(result, ensure_ascii=False).encode('utf8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(ROOT)))
    url = f'http://127.0.0.1:{args.port}/aljabr.html'
    print('ALJABR ready: ' + url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    server.serve_forever()
