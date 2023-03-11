from typing import List

from pydantic import BaseSettings, validator


class DBSettings(BaseSettings):
    MONGODB_CONNECTION_URL: str
    MONGODB_DB: str


class TelegramSettings(BaseSettings):
    ADMINS: List[int]
    BOT_TOKEN: str

    @validator("ADMINS", pre=True)
    def convert_to_list(cls, l) -> List[int]:
        return [int(s) for s in l.split(",")]


class Settings(TelegramSettings, DBSettings):
    pass


settings = Settings()
