from typing import Annotated, cast
from fast_depends import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update
from src.bot.common.context import ApplicationContext

import structlog

from src.bot.errors import UserNotRegistered
from src.db.tables import User

log = structlog.get_logger()


def ConversationState(t: type, clear: bool = False):
    """
    Extractor for user conversation state. If not present will be initialized with the no arg
    constructor for the given type. If `clear` is set to `True` the conversation state will be
    deleted after the handler has been executed.
    Any uncaught exception will result in the conversation state being deleted.
    """

    def extract_state(context: ApplicationContext):
        try:
            yield context.user_data.get_or_init_conversation_state(t)
            if clear:
                context.user_data.clean_up_conversation_state(t)
        except Exception as e:
            context.user_data.clean_up_conversation_state(t)
            raise e

    return Depends(extract_state)



def CallbackQuery(t: type):
    """
    Extractor for callback query data. Raises a `ValueError` if no data is present for the given type.
    """

    def extract_callback_query(update: Update) -> t:
        data = update.callback_query.data
        if data is None:
            raise ValueError(
                "No callback query data for given type {} in update {}".format(
                    t, update
                )
            )
        return cast(t, data)

    return Depends(extract_callback_query)


async def tx(context: ApplicationContext):
    """
    Opens a session and commits it after the handler has been executed. Rollback on uncaught exceptions
    """
    async with context.session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.info(
                "Uncaught Exception during SQLAlchemy session, rolling back transaction",
                reason=e,
            )
            raise e

DBSession = Annotated[AsyncSession, tx]

async def load_user(update: Update, session = Depends(tx)) -> User:
    """
    Extractor for the current user. Requires a `session` dependency to be present in function signature.
    """
    result = await session.execute(
        select(User).where(User.telegram_id == update.effective_user.id)
    )
    if user := result.scalar_one_or_none():
        return user
    else:
        raise UserNotRegistered


CurrentUser = Annotated[User, Depends(load_user)]

