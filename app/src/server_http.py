# server_http.py — minimal stdlib HTTP server (no fastmcp required)
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from typing import Any, Dict

from state_store import StateStore

TOOLS = [
    {
        "name": "add_note",
        "description": "Append a note to a session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "note": {"type": "string"}
            },
            "required": ["session_id", "note"]
        },
    },
    {
        "name": "get_notes",
        "description": "Get notes for a session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"}
            },
            "required": ["session_id"]
        },
    },
    {
        "name": "echo_cached",
        "description": "Echo text but cache result by text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        },
    },
    {
        "name": "reset_session",
        "description": "Delete notes for a session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"}
            },
            "required": ["session_id"]
        },
    },
]

def _ok(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def _error(handler: BaseHTTPRequestHandler, message: str, status: int = 400):
    _ok(handler, {"error": message}, status=status)

def _handle_tool(name: str, args: Dict[str, Any]) -> Any:
    if name == "add_note":
        session_id = args["session_id"]
        note = args["note"]
        StateStore.create_session(session_id)
        StateStore.append_note(session_id, note)
        return "Note added to %s." % session_id

    if name == "get_notes":
        session_id = args["session_id"]
        return StateStore.get_notes(session_id)

    if name == "echo_cached":
        import hashlib, json as _json
        text = args["text"]
        key = hashlib.sha256(_json.dumps({"text": text}, sort_keys=True).encode()).hexdigest()[:16]
        cached = StateStore.get_tool_cache("echo_cached", key)
        if cached:
            return f"[cache] {cached}"
        result = text.upper()
        StateStore.cache_tool_result("echo_cached", key, result, ttl_seconds=900)
        return result

    if name == "reset_session":
        session_id = args["session_id"]
        deleted = StateStore.reset_session(session_id)
        return f"Deleted {deleted} notes from {session_id}."

    raise ValueError(f"Unknown tool: {name}")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/mcp/health":
            return _ok(self, {"status": "ok"})
        if path == "/mcp/list_tools":
            return _ok(self, TOOLS)
        return _error(self, "Not found", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return _error(self, "Invalid JSON", 400)

        if path == "/mcp/call_tool":
            try:
                name = data["name"]
                args = data.get("arguments", {}) or {}
                result = _handle_tool(name, args)
                return _ok(self, {"result": result})
            except Exception as e:
                return _error(self, f"{e}", 400)

        return _error(self, "Not found", 404)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3333)
    args = parser.parse_args()

    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"Serving on http://{args.host}:{args.port}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
