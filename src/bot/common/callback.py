from functools import wraps
from typing import (
    Type,
    Optional,
    Pattern,
)
from pydantic import BaseModel
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
)
from src.bot.common.context import ApplicationContext
import structlog

log = structlog.get_logger()


def regex_callback_query_handler(
    pattern: str | Pattern[str], *, answer_query_after: bool = True
):
    def inner_decorator(f) -> CallbackQueryHandler:
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            result = await f(update, context)
            if answer_query_after:
                await update.callback_query.answer()  # type: ignore
            return result

        return CallbackQueryHandler(pattern=pattern, callback=wrapped)  # type: ignore

    return inner_decorator


def answer_inline_query_after(f):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        result = await f(update, context)
        try:
            await update.callback_query.answer()  # type: ignore
        except Exception as e:
            log.error(f"Failed answering callback_query", error=e)
        finally:
            return result

    return wrapped


def drop_callback_data_after(f):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        result = await f(update, context)
        try:
            context.drop_callback_data(update.callback_query)  # type: ignore
        except KeyError as e:
            log.error(
                f"Failed dropping callback_query_data, couldn't find Key", error=e
            )
        finally:
            return result

    return wrapped


def arbitrary_callback_query_handler(
    query_data_type: Type,
    *,
    answer_query_after: bool = True,
    clear_callback_data: bool = False,
):
    def inner_decorator(f) -> CallbackQueryHandler:
        if answer_query_after:
            f = answer_inline_query_after(f)
        if clear_callback_data:
            f = drop_callback_data_after(f)
        handler = CallbackQueryHandler(pattern=query_data_type, callback=f)
        return handler

    return inner_decorator


class CallbackButton(BaseModel):
    """
    Base class to generate callback buttons with text derived from the class name.

    Example:
    ```
    class DELETE_QUESTION(CallbackButton):
        question_id: int

    button = DELETE_QUESTION(question_id=1).to_short_button()
    ```
    This will create a button with the text "DELETE" and the callback_data
    will be handled by a `CallbackQueryHandler` that has as pattern the type
    `DELETE_QUESTION`.
    """

    def to_short_button(self, *, emoji: Optional[str] = None) -> InlineKeyboardButton:
        text = self.__class__.__name__.split("_")[0]
        if emoji:
            text = f"{emoji} {text} {emoji}"
        return InlineKeyboardButton(text=text, callback_data=self)

    def to_button(
        self, *, text: Optional[str] = None, emoji: Optional[str]
    ) -> InlineKeyboardButton:
        if text is None:
            text = (" ").join(self.__class__.__name__.split("_"))

        if emoji:
            text = f"{emoji} {text} {emoji}"
        return InlineKeyboardButton(text=text, callback_data=self)

    def to_keyboard(
        self, *, text: Optional[str] = None, emoji: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[self.to_button(text=text, emoji=emoji)]])
