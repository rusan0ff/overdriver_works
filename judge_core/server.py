"""HTTP JSON interface for judge_core. Pure stdlib (http.server).

This is the sellable face: a payment bot or a website can POST a scoring
request and get a clean JSON/CSV report back. No framework, no deps.

Run:
    cd C:/Users/iankye/overdriver
    python -m judge_core.server [--port 8765]

Request (POST /score):
    Content-Type: application/json
    {
      "criteria": [{"name": "logic", "weight": 2, "max": 10},
                   {"name": "style", "weight": 1, "max": 5}],
      "values": {"logic": 8, "style": 4},
      "format": "json"        # optional: "json" (default) or "csv"
    }

Response 200 (json):
    {"total": 80.00, "complete": true, "errors": [], "rows": [...]}
Response 400 on bad config (criteria unusable) with a plain error string.
Response 200 on bad DATA but errors filled in (total may be null).

Config error vs data error is preserved: bad criteria -> 400, bad values -> 200+errors.
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from .scorer import Criterion, ScoringConfigError, Scorer


def build_scorer(payload: dict) -> Scorer:
    criteria = payload.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ScoringConfigError("'criteria' must be a non-empty list")
    items = []
    for c in criteria:
        if not isinstance(c, dict):
            raise ScoringConfigError("each criterion must be an object")
        try:
            items.append(Criterion.of(c["name"], c["weight"], c["max"]))
        except KeyError as e:
            raise ScoringConfigError(f"criterion missing field {e}") from e
    return Scorer(items)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: str, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        if self.path == "/health":
            self._send(200, '{"ok": true}')
            return
        self._send(404, '{"error": "not found"}')

    def do_POST(self):
        if self.path != "/score":
            self._send(404, '{"error": "not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            scorer = build_scorer(payload)
        except (ValueError, ScoringConfigError) as e:
            self._send(400, json.dumps({"error": str(e)}))
            return

        values = payload.get("values")
        if not isinstance(values, dict):
            self._send(400, json.dumps({"error": "'values' must be an object"}))
            return

        report = scorer.score(values)
        fmt = payload.get("format", "json")
        if fmt == "csv":
            self._send(200, report.to_csv(), "text/csv; charset=utf-8")
            return
        body = json.dumps({
            "total": float(report.total) if report.total is not None else None,
            "complete": report.complete,
            "errors": report.errors,
            "rows": report.rows,
        })
        self._send(200, body)

    def log_message(self, *args):
        pass  # keep stdout clean


def main(argv=None):
    port = 8765
    if argv:
        for i, a in enumerate(argv):
            if a == "--port" and i + 1 < len(argv):
                port = int(argv[i + 1])
    srv = HTTPServer(("127.0.0.1", port), Handler)
    print(f"judge_core HTTP on 127.0.0.1:{port} (Ctrl+C to stop)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
