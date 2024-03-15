from functools import wraps
from typing import (
    Callable,
    Any,
    Awaitable,
    Coroutine,
)

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.ext.filters import BaseFilter

from src.bot.common.context import ApplicationContext
from src.db.tables import User

import logging

log = logging.getLogger(__name__)


def restricted_action(
    is_allowed: Callable[[Update, ApplicationContext, User], Awaitable[Any]],
    *,
    unauthorized_message: str | None = None,
):
    def inner_decorator(
        f: Callable[[Update, ApplicationContext, User], Awaitable[Any]]
    ):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext, user: User):
            if await is_allowed(update, context, user):
                return await f(update, context, user)
            elif unauthorized_message:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=unauthorized_message  # type: ignore
                )

        return wrapped

    return inner_decorator

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
