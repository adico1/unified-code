"""Generated loopback-only GUI host boundary."""

import argparse
import json
import mimetypes
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from .cli import execute

REQUIRES_ROOT = False
MAXIMUM_REQUEST_BYTES = 1048576


def _response(connection, status, body, content_type):
    payload = body if isinstance(body, bytes) else body.encode("utf-8")
    headers = (
        "HTTP/1.1 " + status + "\r\n"
        "Content-Type: " + content_type + "\r\n"
        "Content-Length: " + str(len(payload)) + "\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ).encode("ascii")
    connection.sendall(headers + payload)


def _receive(connection):
    raw = b""
    while b"\r\n\r\n" not in raw and len(raw) <= MAXIMUM_REQUEST_BYTES:
        block = connection.recv(65536)
        if not block:
            break
        raw += block
    heading, _, body = raw.partition(b"\r\n\r\n")
    lines = heading.decode("iso-8859-1").split("\r\n")
    method, target, _ = lines[0].split(" ", 2)
    headers = dict(line.split(":", 1) for line in lines[1:] if ":" in line)
    length = int(headers.get("Content-Length", "0").strip())
    while len(body) < length and len(body) <= MAXIMUM_REQUEST_BYTES:
        body += connection.recv(min(65536, length - len(body)))
    return method, target.split("?", 1)[0], {key.lower(): value.strip() for key, value in headers.items()}, body[:length]


def _serve(connection, browser_root, authority_root, capability, stop):
    try:
        method, target, headers, body = _receive(connection)
        if method == "POST" and target in ("/api", "/shutdown"):
            if not secrets.compare_digest(headers.get("x-uc-capability", ""), capability):
                _response(connection, "403 Forbidden", '{"error":"capability-required"}', "application/json")
                return
            if target == "/shutdown":
                stop.set()
                _response(connection, "200 OK", '{"stopped":true}', "application/json")
                return
            if len(body) > MAXIMUM_REQUEST_BYTES:
                _response(connection, "413 Content Too Large", '{"error":"request-too-large"}', "application/json")
                return
            try:
                request = json.loads(body.decode("utf-8"))
            except (UnicodeError, ValueError):
                result = {"state":"invalid","output":None,"error":"invalid-host-json","evidence":[]}
            else:
                result = execute(request, str(authority_root))
            _response(connection, "200 OK", json.dumps(result, separators=(",", ":"), sort_keys=True), "application/json")
            return
        relative = "index.html" if target in ("/", "/index.html") else target.removeprefix("/")
        if relative not in ("index.html", "style.css", "browser.js"):
            _response(connection, "404 Not Found", "not found", "text/plain")
            return
        path = browser_root / relative
        payload = path.read_bytes()
        if relative == "browser.js":
            payload = payload.replace(b"__UC_SESSION_CAPABILITY__", capability.encode("ascii"))
        if relative == "index.html":
            payload = payload.replace(b"<html lang=\"en\">", ("<html lang=\"en\" data-uc-root=\"" + str(authority_root).replace("&", "&amp;").replace('"', "&quot;") + "\">").encode("utf-8"))
        _response(connection, "200 OK", payload, mimetypes.guess_type(relative)[0] or "application/octet-stream")
    except (OSError, TypeError, ValueError):
        try:
            _response(connection, "400 Bad Request", "bad request", "text/plain")
        except OSError:
            pass
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(prog='pong_game' + "-gui")
    parser.add_argument("--root")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--proof", action="store_true")
    args = parser.parse_args(argv)
    if REQUIRES_ROOT and not args.root:
        parser.error("--root is required")
    authority_root = Path(args.root or ".").resolve(strict=True)
    browser_root = Path(__file__).resolve().parents[1] / "browser"
    capability = secrets.token_urlsafe(32)
    stop = threading.Event()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(16)
    server.settimeout(0.25)
    port = server.getsockname()[1]
    url = "http://127.0.0.1:" + str(port) + ("/?uc-proof=1" if args.proof else "/")
    sys.stdout.write(json.dumps({"url": url, "host": "127.0.0.1", "port": port}, separators=(",", ":"), sort_keys=True) + "\n")
    sys.stdout.flush()
    if not args.no_open:
        webbrowser.open(url)
    try:
        while not stop.is_set():
            try:
                connection, address = server.accept()
            except socket.timeout:
                continue
            if address[0] != "127.0.0.1":
                connection.close()
                continue
            threading.Thread(target=_serve, args=(connection, browser_root, authority_root, capability, stop), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
    return 0
