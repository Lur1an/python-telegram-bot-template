from pydantic_settings import BaseSettings

class DBSettings(BaseSettings):
    DB_PATH: str = "template_app.db"

class TelegramSettings(BaseSettings):
    BOT_TOKEN: str
    FIRST_ADMIN: int
    LOGGING_CHANNEL: int | None = None

class Settings(TelegramSettings, DBSettings):
    pass
