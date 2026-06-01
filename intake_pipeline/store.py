"""Supabase-backed pipeline status (generic table names)."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

TABLE_STATUS = "intake_batch_status"
TABLE_WATCHLIST = "intake_watchlist"


def get_supabase() -> Client:
    load_dotenv()
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    return create_client(url, key)


def document_exists(sb: Client, document_id: str) -> bool:
    res = sb.table(TABLE_STATUS).select("document_id").eq("document_id", document_id).limit(1).execute()
    return bool(res.data)


def upsert_pending(
    sb: Client,
    *,
    document_id: str,
    source_key: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    row: dict[str, Any] = {
        "document_id": document_id,
        "source_key": source_key,
        "status": "pending",
    }
    if metadata:
        row["metadata"] = metadata
    sb.table(TABLE_STATUS).upsert(row).execute()
