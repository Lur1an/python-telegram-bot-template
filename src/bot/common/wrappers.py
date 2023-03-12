from functools import wraps
from typing import List, Callable, Any, Generic, TypeVar, cast, Awaitable

from telegram import Update
from telegram.ext import ConversationHandler, CallbackQueryHandler

from src.bot.common.context import ApplicationContext

import logging

log = logging.getLogger(__name__)


def admin_command(f: Callable[[Update, ApplicationContext], Awaitable[Any]], admin_ids: List[int]):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        if update.effective_user.id not in admin_ids:
            return
        return await f(update, context)

    return wrapped


CallbackDataType = TypeVar("CallbackDataType")


def arbitrary_callback_query_handler(
        f: Callable[[Update, ApplicationContext, Generic[CallbackDataType]], Awaitable[Any]], answer_query_after: bool = True):
    """
    Transforms this method into a CallbackQueryHandler for the used CallbackDataType, the callback_query.data is injected into the wrapped function
    Automatically answers the callback query when the handler is done.
    """

    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        converted_data = cast(CallbackDataType, update.callback_query.data)
        result = await f(update, context, converted_data)
        if answer_query_after:
            await update.callback_query.answer()
        return result

    return CallbackQueryHandler(pattern=CallbackDataType, callback=wrapped)


def cleanup_chat(f: Callable[[Update, ApplicationContext, list[tuple[int, int]]], Awaitable[Any]]):
    """
    Wrap this telegram callback function to delete all the messages added as tuple(message_id, chat_id)
    to the list parameter in the function definition after finishing the method call
    """

    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        delete_after: list[tuple[int, int]] = list()
        # call method
        result = await f(update, context, delete_after)
        # clean up
        for message_id, chat_id in delete_after:
            try:
                await context.bot.delete_message(
                    message_id=message_id,
                    chat_id=chat_id
                )
            except:
                pass
        return result

    return wrapped


def delete_message_after(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
    @wraps(f)
    async def wrapper(update: Update, context: ApplicationContext):
        result = await f(update, context)
        await context.bot.delete_message(
            message_id=update.effective_message.id,
            chat_id=update.effective_chat.id
        )
        return result

    return wrapper


def exit_conversation_on_exception(
        f: Callable[[Update, ApplicationContext], Any],
        user_message: str = "I'm sorry, something went wrong, try again or contact an Administrator."
):
    """
    Safe catch for any exception that escapes, exits the conversation and notifies the user about the failure
    :param f: callback function
    :param user_message:
    :return:
    """

    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        try:
            return await f(update, context)
        except:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=user_message
            )
            context.chat_data.conversation_data = None
            return ConversationHandler.END

    return wrapped
