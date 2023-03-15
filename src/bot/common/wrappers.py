from functools import wraps
from io import UnsupportedOperation
from typing import List, Callable, Any, Generic, TypeVar, cast, Awaitable, Coroutine, Optional, Pattern

from pydantic import BaseModel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram._utils.types import RT
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler, BaseHandler, MessageHandler, filters
from telegram.ext.filters import BaseFilter

from src.bot.common.context import ApplicationContext

import logging

from src.db.config import db
from src.user.persistence import User, UserDAO

log = logging.getLogger(__name__)


def restricted_action(is_allowed: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            if await is_allowed(update, context):
                return await f(update, context)

        return wrapped

    return inner_decorator


CallbackDataType = TypeVar("CallbackDataType")


def regex_callback_query_handler(
        pattern: str | Pattern[str], *,
        answer_query_after: bool = True
):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]) -> CallbackQueryHandler:
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            await f(update, context)
            if answer_query_after:
                await update.callback_query.answer()

        return CallbackQueryHandler(
            pattern=pattern,
            callback=wrapped
        )


def answer_inline_query_after(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        result = await f(update, context)
        try:
            await update.callback_query.answer()
        except Exception as e:
            log.error(f"Failed answering callback_query: {e}")
        finally:
            return result

    return wrapped


def drop_callback_data_after(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        result = await f(update, context)
        try:
            context.drop_callback_data(update.callback_query)
        except KeyError as e:
            log.error(f"Failed dropping callback_query_data, couldn't find Key: {e}")
        finally:
            return result

    return wrapped


def arbitrary_callback_query_handler(
        query_data_type: CallbackDataType, *,
        inject: bool = True,
        answer_query_after: bool = True,
        clear_callback_data: bool = False
):
    if inject:
        def inner_decorator(
                f: Callable[[Update, ApplicationContext, CallbackDataType], Awaitable[Any]]
        ) -> CallbackQueryHandler:
            decorator = inject_callback_query(
                answer_query_after=answer_query_after,
                clear_callback_data=clear_callback_data
            )
            wrapped = decorator(f)
            handler = CallbackQueryHandler(pattern=query_data_type, callback=wrapped)
            return handler

        return inner_decorator
    else:
        def inner_decorator(
                f: Callable[[Update, ApplicationContext], Awaitable[Any]]
        ) -> CallbackQueryHandler:
            if answer_query_after:
                f = answer_inline_query_after(f)
            if clear_callback_data:
                f = drop_callback_data_after(f)
            handler = CallbackQueryHandler(pattern=query_data_type, callback=f)
            return handler

        return inner_decorator


def inject_callback_query(
        _f: Callable[[Update, ApplicationContext, CallbackDataType], Awaitable[Any]] = None, *,
        answer_query_after: bool = True,
        clear_callback_data: bool = False,
):
    def inner_decorator(f: Callable[[Update, ApplicationContext, CallbackDataType], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            converted_data = cast(CallbackDataType, update.callback_query.data)
            result = await f(update, context, converted_data)

            return result

        if answer_query_after:
            wrapped = answer_inline_query_after(wrapped)
        if clear_callback_data:
            wrapped = drop_callback_data_after(wrapped)

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
        _f: Callable[[Update, ApplicationContext], Any] = None,
        *,
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


def command_handler(command: str, *, allow_group: bool = False):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]]) -> CommandHandler:
        return CommandHandler(
            filters=None if allow_group else filters.ChatType.PRIVATE,
            command=command,
            callback=f
        )

    return inner_decorator


def message_handler(filters: BaseFilter):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]]) -> MessageHandler:
        return MessageHandler(
            filters=filters,
            callback=f
        )

    return inner_decorator


def arbitrary_message_handler(f: Callable[[Update, ApplicationContext], Coroutine[Any, Any, RT]]):
    return MessageHandler(
        filters=filters.ALL, callback=f
    )


def load_user(
        _f: Callable[[Update, ApplicationContext, User], Coroutine[Any, Any, RT]] = None,
        *,
        required: bool = False,
        error_message: Optional[str] = None
):
    def inner_decorator(f: Callable[[Update, ApplicationContext, User], Coroutine[Any, Any, RT]]):
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
            return await f(update, context, user)

        return wrapped

    if _f is None:
        return inner_decorator
    else:
        return inner_decorator(_f)


class CallbackButton(BaseModel):
    def to_short_button(self, *, emoji: Optional[str] = None) -> InlineKeyboardButton:
        text = self.__class__.__name__.split("_")[0]
        if emoji:
            text = f"{emoji} {text} {emoji}"
        return InlineKeyboardButton(text=text, callback_data=self)

    def to_button(self, *, text: Optional[str] = None, emoji: Optional[str]) -> InlineKeyboardButton:
        if text is None:
            text = (' ').join(self.__class__.__name__.split("_"))

        if emoji:
            text = f"{emoji} {text} {emoji}"
        return InlineKeyboardButton(text=text, callback_data=self)

    def to_keyboard(
            self,
            *,
            text: Optional[str] = None,
            emoji: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [self.to_button(text=text, emoji=emoji)]
        ])
