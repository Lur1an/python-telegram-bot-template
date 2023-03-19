from typing import List

from pydantic import BaseSettings, validator


class DBSettings(BaseSettings):
    MONGODB_CONNECTION_URL: str
    MONGODB_DB: str


class TelegramSettings(BaseSettings):
    BOT_TOKEN: str


class Settings(TelegramSettings, DBSettings):
    CACHE_CLEAR_INTERVAL: int = 60 * 60
    CACHE_LIMIT: int = 1000
    pass


settings = Settings()
