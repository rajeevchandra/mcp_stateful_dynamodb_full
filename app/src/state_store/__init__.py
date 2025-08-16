
import os

BACKEND = os.getenv("MCP_STATE_BACKEND", "DYNAMODB").upper()

if BACKEND == "DYNAMODB":
    from .dynamodb_store import StateStore  # noqa: F401
else:
    raise RuntimeError(f"Unsupported MCP_STATE_BACKEND: {BACKEND}")
