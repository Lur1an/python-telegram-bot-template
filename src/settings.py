from pydantic_settings import BaseSettings

class DBSettings(BaseSettings):
    DB_PATH: str = "template_app.d"

class TelegramSettings(BaseSettings):
    BOT_TOKEN: str

class Settings(TelegramSettings, DBSettings):
    pass


settings = Settings() # type: ignore
