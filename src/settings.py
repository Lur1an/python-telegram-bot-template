from pydantic import BaseSettings


class DBSettings(BaseSettings):
    DB_URL: str
    CREATE_TABLES: bool = False


class TelegramSettings(BaseSettings):
    BOT_TOKEN: str


class Settings(TelegramSettings, DBSettings):
    pass


settings = Settings()
