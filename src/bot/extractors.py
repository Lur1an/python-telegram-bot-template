from fast_depends import Depends
from telegram import Update
from src.bot.common.context import ApplicationContext

import logging
log = logging.getLogger(__name__)


def ConversationState(t: type):
    def extract_state(context: ApplicationContext):
        try:
            yield context.user_data.get_conversation_state(t)
        except Exception as e:
            log.error("Unhandled exception in conversation, clearing state", e)
            context.user_data.clean_up_conversation_state(t)
            yield None

    return Depends(extract_state)


async def tx(context: ApplicationContext):
    async with context.session() as session:
        try:
            yield session
        except Exception as e:
            log.error("Unhandled exception in SQL session", e)
            await session.rollback()
