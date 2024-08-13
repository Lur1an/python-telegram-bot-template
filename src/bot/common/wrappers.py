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

import structlog

log = structlog.getLogger()

HandlerFunction = Callable[[Update, ApplicationContext], Coroutine[Any, Any, Any]]


def reply_exception(
    _f: HandlerFunction | None = None,
    condition: Callable[[Update, ApplicationContext], Awaitable[bool]] | None = None,
) -> Any:
    def inner_decorator(f: HandlerFunction):
        async def wrapper(update: Update, context: ApplicationContext):
            try:
                result = await f(update, context)
                return result
            except Exception as e:
                if condition is None or await condition(update, context):
                    await update.effective_message.reply_text(f"An error occurred: {e}")
                raise

        return wrapper

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)


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


def command_handler(command: str | list[str], *, filters: BaseFilter = filters.ALL):
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


def any_message(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, Any]]):
    return MessageHandler(filters=filters.ALL, callback=f)
