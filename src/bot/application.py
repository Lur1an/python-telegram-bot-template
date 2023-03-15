from telegram import Update
from telegram.ext import ApplicationBuilder, Application, ContextTypes

from src.bot.common.context import ApplicationContext, ChatData, BotData, UserData, context_types
from src.db.core import BaseDAO
from src.settings import settings
from src.user.handlers import start


async def on_startup(app):
    app.add_handler(start)
    await BaseDAO.create_all_indexes()


application: Application = ApplicationBuilder() \
    .token(settings.BOT_TOKEN) \
    .context_types(context_types) \
    .arbitrary_callback_data(True) \
    .post_init(on_startup) \
    .build()
