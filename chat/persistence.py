"""Fire-and-forget persistence of Fliss conversations to Postgres.

Uses psycopg2 on a background thread so saves never block chat responses.
Controlled by SAVE_CONVERSATIONS env var. Credentials read from DB_HOST,
DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="fliss-persist")
_schema_lock = threading.Lock()
_schema_ready = False


def _enabled() -> bool:
    return os.getenv("SAVE_CONVERSATIONS", "").lower() in ("1", "true", "yes")


def _connect():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    "sessionId" VARCHAR NOT NULL,
    "userType" VARCHAR,
    location VARCHAR,
    messages JSONB,
    "messageCount" INTEGER,
    "createdAt" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conversations_session
    ON conversations ("sessionId");
"""


def _ensure_schema(conn) -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        with conn.cursor() as cur:
            cur.execute(_CREATE_SQL)
        conn.commit()
        _schema_ready = True


def _serialise_messages(messages: list[dict]) -> str:
    """Coerce API content blocks (non-JSON-serialisable objects) to plain dicts."""
    clean = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, list):
            blocks = []
            for b in content:
                if hasattr(b, "model_dump"):
                    blocks.append(b.model_dump())
                elif isinstance(b, dict):
                    blocks.append(b)
                else:
                    blocks.append({"text": str(b)})
            content = blocks
        clean.append({"role": role, "content": content})
    return json.dumps(clean, default=str)


_UPSERT_SQL = """
WITH updated AS (
    UPDATE conversations
    SET messages = %s::jsonb,
        "messageCount" = %s,
        "userType" = %s,
        location = COALESCE(%s, location),
        "updatedAt" = CURRENT_TIMESTAMP
    WHERE "sessionId" = %s
    RETURNING id
)
INSERT INTO conversations ("sessionId", "userType", location, messages, "messageCount")
SELECT %s, %s, %s, %s::jsonb, %s
WHERE NOT EXISTS (SELECT 1 FROM updated);
"""


def _save_sync(
    session_id: str,
    user_type: str | None,
    location: str | None,
    messages: list[dict],
) -> None:
    try:
        payload = _serialise_messages(messages)
        count = len(messages)
        conn = _connect()
        try:
            _ensure_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    _UPSERT_SQL,
                    (
                        payload, count, user_type, location, session_id,
                        session_id, user_type, location, payload, count,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"[persistence] Failed to save conversation {session_id}: {e}")


def save_conversation(
    session_id: str,
    user_type: str | None,
    location: str | None,
    messages: list[dict],
) -> None:
    """Fire-and-forget save. No-op if SAVE_CONVERSATIONS is not enabled."""
    if not _enabled() or not session_id:
        return
    _executor.submit(_save_sync, session_id, user_type, location, list(messages))
