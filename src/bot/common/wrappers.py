from functools import wraps
from typing import List, Callable, Any, Generic, TypeVar, cast, Awaitable, Coroutine, Optional

from telegram import Update
from telegram._utils.types import RT
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler, BaseHandler

from src.bot.common.context import ApplicationContext

import logging

from src.db.config import db
from src.user.persistence import User, UserDAO

log = logging.getLogger(__name__)


def restricted_action(allowed_users: List[int]):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            if update.effective_user.id not in allowed_users:
                return
            return await f(update, context)

        return wrapped

    return inner_decorator


CallbackDataType = TypeVar("CallbackDataType")


def arbitrary_callback_query_handler(
        query_data_type: CallbackDataType, *,
        answer_query_after: bool = True
):
    def inner_decorator(
            f: Callable[[Update, ApplicationContext, Generic[CallbackDataType]], Awaitable[Any]]
    ) -> CallbackQueryHandler:
        decorator = inject_callback_query(answer_query_after=answer_query_after)
        wrapped = decorator(f)
        handler = CallbackQueryHandler(pattern=query_data_type, callback=wrapped)
        return handler

    return inner_decorator


def inject_callback_query(
        _f: Callable[[Update, ApplicationContext, Generic[CallbackDataType]], Awaitable[Any]] = None, *,
        answer_query_after: bool = True
):
    def inner_decorator(f: Callable[[Update, ApplicationContext, Generic[CallbackDataType]], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            converted_data = cast(CallbackDataType, update.callback_query.data)
            result = await f(update, context, converted_data)
            if answer_query_after:
                await update.callback_query.answer()
            return result

        return wrapped

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
                message_id=update.effective_message.id,
                chat_id=update.effective_chat.id
            )
        finally:
            return result

    return wrapper


def exit_conversation_on_exception(
        _f: Callable[[Update, ApplicationContext], Any] = None, *,
        user_message: str = "I'm sorry, something went wrong, try again or contact an Administrator."
):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Any]):

        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            try:
                return await f(update, context)
            except Exception as e:
                log.error(f"Encountered an error while handling conversation step: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=user_message
                )
                context.chat_data.conversation_data = None
                return ConversationHandler.END

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)


def command_handler(command: str):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]]) -> CommandHandler:
        return CommandHandler(
            command=command,
            callback=f
        )

    return inner_decorator


def load_user(
        _f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]] = None,
        *,
        required: bool = False,
        error_message: Optional[str] = None
):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            user = context.get_cached_user(update.effective_user.id)
            if user is None:
                dao = UserDAO(db)
                user = await dao.find_by_telegram_id(update.effective_user.id)
                context.cache_user(user)
            if user is None and required:
                if error_message is not None:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=error_message
                    )
                return
            return await f(update, context)

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)


def next_reply_handler(entry_point: BaseHandler[Update, Any]):
    def inner_decorator(handler: BaseHandler[Update, Any]):

        @exit_conversation_on_exception
        async def wrapped_entrypoint_callback(update: Update, context: ApplicationContext):
            await entry_point.callback(update, context)
            return 1

        entry_point.callback = wrapped_entrypoint_callback

        async def wrapped_handler_callback(update: Update, context: ApplicationContext):
            try:
                await handler.callback(update, context)
            finally:
                return ConversationHandler.END

        @command_handler("cancel")
        async def cancel(update: Update, context: ApplicationContext):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Aborting procedure...")
            return ConversationHandler.END

        handler.callback = wrapped_handler_callback
        return ConversationHandler(
            entry_points=[entry_point],
            states={
                1: [handler]
            },
            fallbacks=[cancel]
        )

    return inner_decorator
