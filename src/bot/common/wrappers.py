from functools import wraps
from typing import (
    Callable,
    Any,
    TypeVar,
    Awaitable,
    Coroutine,
    Optional,
)

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.ext.filters import BaseFilter

from src.bot.common.context import ApplicationContext

import logging

from src.db.config import db
from src.user.persistence import UserDAO

log = logging.getLogger(__name__)


def restricted_action(
    is_allowed: Callable[[Update, ApplicationContext], Awaitable[Any]]
):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            if await is_allowed(update, context):
                return await f(update, context)

        return wrapped

    return inner_decorator


CallbackDataType = TypeVar("CallbackDataType")


def delete_message_after(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    @wraps(f)
    async def wrapper(update: Update, context: ApplicationContext):
        result = await f(update, context)
        try:
            await context.bot.delete_message(
                message_id=update.effective_message.id, chat_id=update.effective_chat.id  # type: ignore
            )
        finally:
            return result

    return wrapper


def exit_conversation_on_exception(
    _f=None,
    *,
    user_message: str = "I'm sorry, something went wrong, try again or contact an Administrator.",
):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Any]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            try:
                return await f(update, context)
            except Exception as e:
                log.error(f"Encountered an error while handling conversation step: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=user_message  # type: ignore
                )
                context.chat_data.conversation_data = None  # type: ignore
                return ConversationHandler.END

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)


def command_handler(command: str, *, filters: BaseFilter = filters.ALL):
    def inner_decorator(
        f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, Any]]
    ) -> CommandHandler:
        return CommandHandler(
            filters=filters,
            command=command,
            callback=f,
        )

    return inner_decorator


def message_handler(filters: BaseFilter):
    def inner_decorator(
        f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, Any]]
    ) -> MessageHandler:
        return MessageHandler(filters=filters, callback=f)

    return inner_decorator


def arbitrary_message_handler(
    f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, Any]]
):
    return MessageHandler(filters=filters.ALL, callback=f)


def load_user(
    _f=None,
    *,
    required: bool = False,
    error_message: Optional[str] = None,
):
    def inner_decorator(f):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            user = context.get_cached_user(update.effective_user.id)
            if user is None:
                user = await UserDAO(db).find_by_telegram_id(update.effective_user.id)
            if user is None and required:
                if error_message is not None:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id, text=error_message
                    )
                return
            if user is not None:
                context.cache_user(user)
            return await f(update, context, user)

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)
