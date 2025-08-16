import requests
import json

BASE = "http://127.0.0.1:3333/mcp"  # adjust if your server runs elsewhere

def call_tool(name, args):
    url = f"{BASE}/call_tool"
    payload = {"name": name, "arguments": args}
    resp = requests.post(url, json=payload)
    try:
        return resp.json()
    except Exception:
        print("Raw response:", resp.text)
        return None

if __name__ == "__main__":
    session = "demo"

    print("1) Adding notes...")
    print(call_tool("add_note", {"session_id": session, "note": "first note"}))
    print(call_tool("add_note", {"session_id": session, "note": "second note"}))

    print("\n2) Getting notes...")
    print(call_tool("get_notes", {"session_id": session}))

    print("\n3) Echo cached test...")
    print(call_tool("echo_cached", {"text": "hello world"}))
    print(call_tool("echo_cached", {"text": "hello world"}))  # should return [cache]

    print("\n4) Resetting session...")
    print(call_tool("reset_session", {"session_id": session}))
    print(call_tool("get_notes", {"session_id": session}))
