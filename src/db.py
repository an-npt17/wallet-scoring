"""Initialize beanie ORM from MONGO_SOURCE_URL environment variable."""

import os

from beanie import init_beanie
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

from database.mongo.schema import (
    Account,
    ClosedPosition,
    DailyTraderRanking,
    Log,
)

_DB_NAME = "perpetuals_knowledge_graph"

_ = load_dotenv()


async def init_db() -> None:
    url = os.environ["MONGO_SOURCE_URL"]
    client: AsyncMongoClient = AsyncMongoClient(url, uuidRepresentation="standard")  # type: ignore[type-arg]
    await init_beanie(
        database=client[_DB_NAME],
        document_models=[Log, Account, ClosedPosition, DailyTraderRanking],
    )
