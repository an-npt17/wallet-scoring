from config.db_config import MongoConfig

mongo_config = MongoConfig()


class Configs:
    @staticmethod
    def get_mongo_config() -> MongoConfig:
        return mongo_config
