"""
Vercel Serverless Function — Telegram Webhook Endpoint
Route: /api/webhook
"""
import json
import sys
import os

# Make sure parent directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import process_update


def handler(request, response=None):
    """
    Vercel Python serverless handler.
    Compatible with Vercel's Python runtime (WSGI / raw handler).
    """
    # ── Vercel calls this as a WSGI-style callable ──
    # But for simple webhook we support both styles.

    if callable(getattr(request, "get_json", None)):
        # Flask-style (if using Flask adapter)
        data = request.get_json(force=True, silent=True) or {}
    elif hasattr(request, "body"):
        # Raw Vercel request object
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
    else:
        data = {}

    try:
        process_update(data)
    except Exception as e:
        print(f"[Handler Error] {e}")

    # Always return 200 to Telegram
    return _ok_response()


def _ok_response():
    """Return a minimal HTTP 200 response."""

    class SimpleResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}

        def __call__(self, environ, start_response):
            start_response(
                "200 OK",
                [("Content-Type", "application/json")],
            )
            return [b'{"ok":true}']

    return SimpleResponse()


# ── WSGI app entry for Vercel ──────────────────────────────────────────────────
def app(environ, start_response):
    """
    Vercel Python Runtime WSGI entry point.
    Vercel sets VERCEL_REGION env var and calls this function.
    """
    method = environ.get("REQUEST_METHOD", "GET")

    if method == "GET":
        # Health check
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"status":"SentinelAI Bot is running"}']

    if method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
            body   = environ["wsgi.input"].read(length)
            data   = json.loads(body.decode("utf-8")) if body else {}
            process_update(data)
        except Exception as e:
            print(f"[WSGI Error] {e}")

        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"ok":true}']

    start_response("405 Method Not Allowed", [("Content-Type", "application/json")])
    return [b'{"error":"Method not allowed"}']
