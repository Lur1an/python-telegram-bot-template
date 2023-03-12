from telegram.ext import ApplicationBuilder, Application, ContextTypes

from src.bot.common.context import ApplicationContext, ChatData, BotData, UserData, context_types
from src.settings import settings


async def on_startup(app: Application):
    pass


application: Application = ApplicationBuilder() \
    .token(settings.BOT_TOKEN) \
    .context_types(context_types) \
    .arbitrary_callback_data(True) \
    .post_init(on_startup) \
    .build()
