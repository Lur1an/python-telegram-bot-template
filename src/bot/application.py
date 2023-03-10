from telegram.ext import ApplicationBuilder, Application

from src.db.config import engine, Base
from src.settings import settings


async def on_startup(application: Application):
    if settings.CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    bot = application.bot


application: Application = ApplicationBuilder() \
    .token(settings.BOT_TOKEN) \
    .post_init(on_startup) \
    .build()
