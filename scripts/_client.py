"""
Shared read-only MongoDB client for analysis scripts.

Reads MONGO_SOURCE_URL from environment. The URL must point to a MongoDB
instance that contains the perpetuals_knowledge_graph database.

Usage:
    export MONGO_SOURCE_URL="mongodb://user:pass@host:port/"
    uv run python scripts/01_accounts_overview.py
"""

import argparse
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

_DB_NAME = "perpetuals_knowledge_graph"
_ = load_dotenv()

_client: AsyncMongoClient | None = None  # type: ignore[type-arg]


def _make_client() -> AsyncMongoClient:  # type: ignore[type-arg]
    url = os.environ["MONGO_SOURCE_URL"]
    return AsyncMongoClient(url, uuidRepresentation="standard")


def get_db() -> AsyncDatabase:  # type: ignore[type-arg]
    global _client
    _client = _make_client()
    return _client[_DB_NAME]


def get_collection(name: str) -> AsyncCollection:  # type: ignore[type-arg]
    return get_db()[name]


async def close_client() -> None:
    """
    Call at the end of main() to cleanly shut down the client before the
    event loop exits — prevents pymongo background tasks from being cancelled
    mid-operation (_OperationCancelled).
    """
    global _client
    if _client is not None:
        _ = await _client.close()
        _client = None


@asynccontextmanager
async def db_context() -> AsyncGenerator[AsyncDatabase, None]:  # type: ignore[type-arg]
    """Async context manager that guarantees client.close() on exit."""
    client = _make_client()
    try:
        yield client[_DB_NAME]
    finally:
        await client.close()


def add_time_range_args(parser: argparse.ArgumentParser) -> None:
    """
    Adds --start/--end date flags so EDA scripts can scope to a window
    instead of scanning the whole collection.
    """
    parser.add_argument(
        "--start", type=str, default=None, help="Start date YYYY-MM-DD (inclusive)"
    )
    parser.add_argument(
        "--end", type=str, default=None, help="End date YYYY-MM-DD (exclusive)"
    )


def date_to_ts(date_str: str) -> int:
    return int(
        datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    )


def time_match_stage(
    field: str, start: str | None, end: str | None
) -> dict[str, dict[str, int]]:
    """
    Builds a MongoDB filter dict restricting `field` (a unix-timestamp field)
    to [start, end). Returns {} (no filter) when both bounds are unset.
    """
    cond: dict[str, int] = {}
    if start:
        cond["$gte"] = date_to_ts(start)
    if end:
        cond["$lt"] = date_to_ts(end)
    return {field: cond} if cond else {}
