from typing import cast
from telegram import Update
import telegram

from src.bot.common.context import ApplicationContext
from src.bot.common.wrappers import command_handler
from src.db.config import db
from src.user.persistence import UserDAO, User


@command_handler("start")
async def start(update: Update, context: ApplicationContext):
    dao = UserDAO(db)
    eu = cast(telegram.User, update.effective_user)
    if context.get_cached_user(eu.id) or await dao.exists(telegram_id=eu.id):
        return
    user_entity = User(
        telegram_id=eu.id,
        telegram_username=eu.username,
        is_bot=eu.is_bot
    )
    await dao.insert(user_entity)

