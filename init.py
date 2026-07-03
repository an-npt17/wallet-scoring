import asyncio

from beanie import init_beanie  # pyright: ignore[reportUnknownVariableType]

from clients import mongo_client
from database.mongo.schema import Account, Log


async def init():
    await init_beanie(
        database=mongo_client.get_database(),
        document_models=[Account, Log],
        allow_index_dropping=True,
    )


if __name__ == "__main__":
    asyncio.run(init())
