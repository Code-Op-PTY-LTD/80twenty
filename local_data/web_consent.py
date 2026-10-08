#!/usr/bin/env python3
"""Participant-visible, loopback-only consent page."""

from __future__ import annotations

import argparse
import html
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from local_data.consent_broker import CONFIRMATION, disclosure, write_consent_record


STYLE = """
body { background:#0d1117; color:#e6edf3; font:16px/1.5 system-ui; margin:0; }
main { max-width:820px; margin:40px auto; padding:32px; background:#161b22;
       border:1px solid #30363d; border-radius:14px; }
h1 { margin-top:0; } pre { white-space:pre-wrap; background:#0d1117; padding:20px;
     border-radius:8px; border:1px solid #30363d; }
label { display:block; margin:20px 0; } input[type=text] { width:100%; box-sizing:border-box;
       padding:12px; color:#e6edf3; background:#0d1117; border:1px solid #8b949e; border-radius:6px; }
button { padding:12px 18px; border:0; border-radius:7px; font-weight:700; margin-right:10px; }
.approve { background:#238636; color:white; } .decline { background:#30363d; color:white; }
.error { color:#ff7b72; font-weight:700; }
"""


def page(title: str, body: str) -> bytes:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head>"
        f"<body><main>{body}</main></body></html>"
    ).encode()


def serve(
    *, root: Path, files: list[str], output_dir: str, receipt: Path,
    max_total_bytes: int, host: str, port: int,
) -> None:
    root = root.resolve()
    for name in files:
        candidate = (root / name).resolve()
        if root not in candidate.parents or candidate.is_symlink() or not candidate.is_file():
            raise ValueError("a requested file is outside the repository, a symlink, or absent")
    notice = disclosure(files, output_dir, max_total_bytes)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            return

        def send(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            if urlparse(self.path).path != "/" or query.get("token") != [token]:
                self.send(404, page("Not found", "<h1>Not found</h1>"))
                return
            body = (
                "<h1>KIN local-data opt-in</h1>"
                f"<pre>{html.escape(notice)}</pre>"
                "<form method='post' action='/consent'>"
                f"<input type='hidden' name='token' value='{html.escape(token)}'>"
                "<label><input type='checkbox' name='ack' value='yes'> "
                "I have read the scope, risks and withdrawal limitation.</label>"
                f"<label>Type <strong>{CONFIRMATION}</strong><input type='text' name='phrase' autocomplete='off'></label>"
                "<button class='approve' name='decision' value='approve'>Approve local training</button>"
                "<button class='decline' name='decision' value='decline'>Decline</button>"
                "</form>"
            )
            self.send(200, page("KIN local-data opt-in", body))

        def do_POST(self) -> None:
            if self.path != "/consent":
                self.send(404, page("Not found", "<h1>Not found</h1>"))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 4096:
                self.send(400, page("Invalid request", "<h1>Invalid request</h1>"))
                return
            fields = parse_qs(self.rfile.read(length).decode("utf-8"))
            if fields.get("token") != [token]:
                self.send(403, page("Forbidden", "<h1>Invalid session token</h1>"))
                return
            if fields.get("decision") == ["decline"]:
                self.send(200, page("Declined", "<h1>Declined</h1><p>No consent receipt was created. No training-file content was read.</p>"))
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if fields.get("ack") != ["yes"] or fields.get("phrase") != [CONFIRMATION]:
                self.send(400, page("Not approved", "<h1>Not approved</h1><p class='error'>The acknowledgement and exact phrase are both required.</p>"))
                return
            write_consent_record(
                root=root,
                files=files,
                output_dir=output_dir,
                receipt_path=receipt,
                max_total_bytes=max_total_bytes,
                notice=notice,
                interaction_channel="loopback_web",
            )
            self.send(200, page("Consent recorded", "<h1>Consent recorded</h1><p>The scoped local receipt was created. You may close this tab.</p>"))
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    server = ThreadingHTTPServer((host, port), Handler)
    actual_port = server.server_address[1]
    print(f"http://{host}:{actual_port}/?token={token}", flush=True)
    server.serve_forever()
    server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--file", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--max-total-bytes", type=int, default=2_000_000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1"}:
        raise SystemExit("consent UI must bind to loopback")
    serve(
        root=args.root, files=args.file, output_dir=args.output_dir,
        receipt=args.receipt, max_total_bytes=args.max_total_bytes,
        host=args.host, port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

