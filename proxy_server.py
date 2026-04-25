#!/usr/bin/env python3
"""
Simple CSV proxy for the leaderboard dashboard.

Run:
  python3 proxy_server.py

Optional env vars:
  PORT=8000
  TARGET_CSV_URL="https://..."
"""

import os
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

DEFAULT_TARGET = (
    "https://data.testbook.com/api/queries/18368/results.csv"
    "?api_key=C1lOpwRYYaDDmZP9INwKEVcErtMdnxG2ey7fwkGY"
)

# Build an opener that ignores system proxy env vars.
# This avoids tunnel/proxy 403 errors on some networks.
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def with_cache_bust(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["_t"] = [str(int(os.times().elapsed * 1000))]
    encoded_query = urlencode(query, doseq=True)
    return parsed._replace(query=encoded_query).geturl()


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "LeaderboardCSVProxy/1.0"

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path_only = parsed_path.path
        if path_only not in ("/sheet.csv", "/healthz", "/"):
            self.send_response(404)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        if path_only == "/healthz":
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        target = os.getenv("TARGET_CSV_URL", DEFAULT_TARGET)
        fetch_url = with_cache_bust(target)

        try:
            req = urllib.request.Request(
                fetch_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (LeaderboardCSVProxy/1.0)",
                    "Accept": "text/csv,text/plain,*/*",
                },
            )
            with NO_PROXY_OPENER.open(req, timeout=30) as res:
                body = res.read()
                content_type = res.headers.get("Content-Type", "text/csv; charset=utf-8")
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", "replace")[:500]
            except Exception:
                err_body = ""
            self.send_response(502)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            payload = {
                "error": "upstream_http_error",
                "status": e.code,
                "url": target,
                "details": err_body,
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        except Exception as e:
            self.send_response(502)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            msg = '{"error":"upstream_fetch_failed","details":"%s"}' % str(e).replace('"', "'")
            self.wfile.write(msg.encode("utf-8"))
            return

        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"CSV proxy running on http://localhost:{port}")
    print("Endpoints: /sheet.csv, /healthz")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

