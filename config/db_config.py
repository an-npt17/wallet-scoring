from pydantic import BaseModel

from config import root_config

db_config = root_config.database


class MongoCollection(BaseModel):
    name: str
    fields_to_index: list[str]
    fields_to_unique: list[str] = []


class MongoConfig:
    USERNAME: str = db_config.mongo.username
    PASSWORD: str = db_config.mongo.password
    HOST: str = db_config.mongo.host
    PORT: int = db_config.mongo.external_port
    LINK: str = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"
    DATABASE: str = db_config.mongo.database
