from clients.mongo import Client as MongoClient


class Clients:
    _mongo_client: MongoClient | None = None

    @classmethod
    def get_mongo_client(cls) -> MongoClient:
        if not cls._mongo_client:
            cls._mongo_client = MongoClient()
        return cls._mongo_client

    @classmethod
    async def close(cls) -> None:
        if cls._mongo_client:
            _ = await cls._mongo_client.close()


mongo_client = Clients.get_mongo_client()

__all__ = ["mongo_client"]
