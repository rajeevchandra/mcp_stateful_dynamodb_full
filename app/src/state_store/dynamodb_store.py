
import os
import time
import json
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

TABLE = os.environ.get("MCP_STATE_TABLE", "mcp_state")
REGION = os.environ.get("AWS_REGION")  # falls back to default provider chain if None
dynamo = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)

def _pk_session(session_id: str) -> str:
    return f"SESSION#{session_id}"

def _pk_tool(tool: str) -> str:
    return f"TOOL#{tool}"

class StateStore:
    """Thin wrapper around DynamoDB for session context + tool cache."""

    @staticmethod
    def create_session(session_id: str, user_id: Optional[str] = None) -> None:
        try:
            dynamo.put_item(
                Item={
                    "pk": _pk_session(session_id),
                    "sk": "META",
                    "userId": user_id or "anonymous",
                    "createdAt": int(time.time()),
                    "lastActive": int(time.time()),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as e:
            # If ConditionalCheckFailed, session already exists — ignore.
            if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise

    @staticmethod
    def append_note(session_id: str, note: str) -> None:
        ts = int(time.time())
        # Append note line
        dynamo.put_item(
            Item={
                "pk": _pk_session(session_id),
                "sk": f"NOTE#{ts}",
                "note": note,
                "ts": ts,
            }
        )
        # Touch lastActive
        dynamo.update_item(
            Key={"pk": _pk_session(session_id), "sk": "META"},
            UpdateExpression="SET lastActive=:t",
            ExpressionAttributeValues={":t": ts},
        )

    @staticmethod
    def get_notes(session_id: str, limit: int = 200) -> List[str]:
        resp = dynamo.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :pfx)",
            ExpressionAttributeValues={":pk": _pk_session(session_id), ":pfx": "NOTE#"},
            Limit=limit,
            ScanIndexForward=True,  # chronological
        )
        return [item.get("note", "") for item in resp.get("Items", [])]

    
    @staticmethod
    def reset_session(session_id: str) -> int:
        """Delete all NOTE# items for a session. Keep META."""
        # Query NOTE# items first
        resp = dynamo.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :pfx)",
            ExpressionAttributeValues={":pk": _pk_session(session_id), ":pfx": "NOTE#"},
            ScanIndexForward=True,
        )
        items = resp.get("Items", [])
        count = 0

        # Use a batch_writer() context manager to delete efficiently
        with dynamo.batch_writer() as batch:
            for it in items:
                batch.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})
                count += 1

        return count


    @staticmethod
    def get_tool_cache(tool: str, key_hash: str) -> Optional[Any]:
        resp = dynamo.get_item(Key={"pk": _pk_tool(tool), "sk": f"KEY#{key_hash}"})
        item = resp.get("Item")
        if not item:
            return None
        try:
            return json.loads(item.get("value", "null"))
        except json.JSONDecodeError:
            return item.get("value")
        
    @staticmethod
    def cache_tool_result(tool_name: str, key: str, value, ttl_seconds: int = 900) -> None:
        expires = int(time.time()) + ttl_seconds
        dynamo.put_item(
            Item={
                "pk": f"TOOL#{tool_name}",
                "sk": f"KEY#{key}",
                "value": json.dumps(value),
                "expiresAt": expires
            }
        )
