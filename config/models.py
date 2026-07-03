from pydantic import BaseModel


# --------------------------------
# DATABASE
# --------------------------------
class MongoConfig(BaseModel):
    host: str
    internal_port: int
    external_port: int
    username: str
    password: str
    database: str


class DatabaseConfig(BaseModel):
    mongo: MongoConfig


# --------------------------------
# ROOT CONFIG
# --------------------------------
class RootConfig(BaseModel):
    database: DatabaseConfig
