"""
Shared read-only MongoDB client for analysis scripts.

Reads MONGO_SOURCE_URL from environment. The URL must point to a MongoDB
instance that contains the perpetuals_knowledge_graph database.

Usage:
    export MONGO_SOURCE_URL="mongodb://user:pass@host:port/"
    uv run python scripts/01_accounts_overview.py
"""

import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

_DB_NAME = "perpetuals_knowledge_graph"
_ = load_dotenv()


def get_db() -> AsyncDatabase:  # type: ignore[type-arg]
    url = os.environ["MONGO_SOURCE_URL"]
    client: AsyncMongoClient = AsyncMongoClient(url, uuidRepresentation="standard")
    return client[_DB_NAME]


def get_collection(name: str) -> AsyncCollection:  # type: ignore[type-arg]
    return get_db()[name]
