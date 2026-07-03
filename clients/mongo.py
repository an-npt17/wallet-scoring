from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from config.settings import mongo_config


class Client:
    root: AsyncMongoClient[Any] = AsyncMongoClient(mongo_config.LINK)
    database: AsyncDatabase[Any] = root[mongo_config.DATABASE]

    def get_root(self) -> AsyncMongoClient[Any]:
        return self.root

    def get_database(self) -> AsyncDatabase[Any]:
        return self.database

    async def close(self) -> None:
        _ = await self.root.close()
