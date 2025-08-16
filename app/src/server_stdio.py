
import asyncio
from mcp.server import Server, stdio_server
from mcp.types import Tool, TextContent, ToolRequest, ToolResponse, Error, ErrorCode
from typing import Dict, Any
import hashlib, json, os

from state_store import StateStore

server = Server("stateful-mcp-dynamodb")

# Define tools
TOOLS = [
    Tool(name="add_note", description="Append a note to a session", inputSchema={
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "note": {"type": "string"}
        },
        "required": ["session_id", "note"]
    }),
    Tool(name="get_notes", description="Get notes for a session", inputSchema={
        "type": "object",
        "properties": {
            "session_id": {"type": "string"}
        },
        "required": ["session_id"]
    }),
    Tool(name="echo_cached", description="Echo text but cache result by text", inputSchema={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        },
        "required": ["text"]
    }),
    Tool(name="reset_session", description="Delete notes for a session", inputSchema={
        "type": "object",
        "properties": {
            "session_id": {"type": "string"}
        },
        "required": ["session_id"]
    }),
]

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS

def _hash_key(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> ToolResponse:
    try:
        if name == "add_note":
            session_id = arguments["session_id"]
            note = arguments["note"]
            StateStore.create_session(session_id)
            StateStore.append_note(session_id, note)
            return ToolResponse(content=[TextContent(type="text", text=f"Note added to {session_id}.")])

        if name == "get_notes":
            session_id = arguments["session_id"]
            notes = StateStore.get_notes(session_id)
            return ToolResponse(content=[TextContent(type="text", text=json.dumps(notes))])

        if name == "echo_cached":
            text = arguments["text"]
            key = _hash_key({"text": text})
            cached = StateStore.get_tool_cache("echo_cached", key)
            if cached:
                return ToolResponse(content=[TextContent(type="text", text=f"[cache] {cached}")])
            # compute (demo)
            result = text.upper()
            StateStore.cache_tool_result("echo_cached", key, result, ttl_seconds=900)
            return ToolResponse(content=[TextContent(type="text", text=result)])

        if name == "reset_session":
            session_id = arguments["session_id"]
            deleted = StateStore.reset_session(session_id)
            return ToolResponse(content=[TextContent(type="text", text=f"Deleted {deleted} notes from {session_id}.")])

        return ToolResponse(isError=True, content=[TextContent(type="text", text=f"Unknown tool: {name}")])
    except Exception as e:
        return ToolResponse(isError=True, content=[TextContent(type="text", text=f"Error: {e}")] )

async def main():
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1])

if __name__ == "__main__":
    asyncio.run(main())
