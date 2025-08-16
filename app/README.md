
# Stateful MCP Server (Python) with DynamoDB

This is a minimal **Model Context Protocol (MCP)** server that persists session context and tool caches to **Amazon DynamoDB**.  
You can run it via **STDIO** (for Claude Desktop / Cline / Cursor) or as an **HTTP/SSE** server for remote usage.

## Features
- Long-lived server that **remembers context** by session id
- **DynamoDB** state store with simple schema (PK/SK), plus TTL support for caches
- Tools:
  - `add_note(session_id, note)` — append a note to session context
  - `get_notes(session_id)` — fetch session notes
  - `echo_cached(text)` — returns cached result if called again (demonstrates caching)
  - `reset_session(session_id)` — clears session context
- Switchable adapter layer if you later add Redis, etc.

---

## 1) Prereqs

- Python 3.10+
- AWS credentials with access to DynamoDB (profile or env vars)
- Create the table (one-time):

```bash
aws dynamodb create-table   --table-name mcp_state   --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S   --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE   --billing-mode PAY_PER_REQUEST

# (Optional but recommended) Enable TTL on the 'expiresAt' attribute for cache cleanup
aws dynamodb update-time-to-live --table-name mcp_state   --time-to-live-specification "Enabled=true, AttributeName=expiresAt"
```
> If table already exists, you can skip this.

**IAM (attach to your role/user):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:DeleteItem"
    ],
    "Resource": [
      "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/mcp_state",
      "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/mcp_state/index/*"
    ]
  }]
}
```

Set environment (you can also use a `.env` file):
```bash
export MCP_STATE_BACKEND=DYNAMODB
export MCP_STATE_TABLE=mcp_state
export AWS_REGION=<your-region>  # e.g., us-east-1
# Optionally set AWS_PROFILE instead of static keys
```

---

## 2) Install

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3) Run — STDIO (for Claude Desktop / Cursor / Cline)

```bash
python src/server_stdio.py
```

Configure your client to launch the executable above as an **STDIO MCP server**.
- For Claude Desktop, add to `claude_desktop_config.json` with type `stdio` and the command `python`, args `["src/server_stdio.py"]`.

---

## 4) Run — HTTP/SSE (for remote HTTP clients)

```bash
python src/server_http.py  --host 0.0.0.0 --port 3333
```
Then point an MCP HTTP client (that supports SSE/HTTP) at `http://localhost:3333/mcp`.

---

## 5) Try the tools

From a compatible client, call tools:

- `add_note` with `{ "session_id": "demo", "note": "first note" }`
- `get_notes` with `{ "session_id": "demo" }` → returns `["first note", ...]`
- `echo_cached` with `{ "text": "hello world" }` → first call computes, second call returns cached
- `reset_session` with `{ "session_id": "demo" }`

You should see items created in your DynamoDB table.

---

## 6) Project Layout

```
mcp_stateful_dynamodb/
├─ README.md
├─ requirements.txt
├─ pyproject.toml
├─ src/
│  ├─ state_store/
│  │  ├─ __init__.py
│  │  └─ dynamodb_store.py
│  ├─ server_stdio.py
│  └─ server_http.py
├─ Dockerfile
└─ .env.example
```

---

## 7) Docker (optional, local)

```bash
docker build -t mcp-dynamodb:local .
docker run --rm -it -p 3333:3333   -e MCP_STATE_BACKEND=DYNAMODB   -e MCP_STATE_TABLE=mcp_state   -e AWS_REGION=us-east-1   -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=...   mcp-dynamodb:local python src/server_http.py --host 0.0.0.0 --port 3333
```

> Prefer using a proper IAM role when running on ECS/Fargate.

---

## 8) Notes
- This server stores *notes* and *small payloads* for demo. For larger objects, store in S3 and keep references in DynamoDB.
- Add retries/backoff around DynamoDB calls for production.
- For ECS, use task role with the IAM JSON above and keep credentials out of env.
- You can extend this with idempotency keys, job tracking, etc.

Happy testing!
