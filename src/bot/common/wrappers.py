from functools import wraps
from typing import List, Callable, Any, Generic, TypeVar, cast, Awaitable

from telegram import Update

from src.bot.common.context import ApplicationContext


def admin_command(f: Callable[[Update, ApplicationContext], Awaitable[Any]], admin_ids: List[int]):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        if update.effective_user.id not in admin_ids:
            return
        return await f(update, context)

    return wrapped


CallbackDataType = TypeVar("CallbackDataType")


def inject_callback_data(f: Callable[[Update, ApplicationContext, Generic[CallbackDataType]], Awaitable[Any]]):
    """
    Automatically extracts callback_data as the correct typeFrom the callback_query and injects it into the wrapped handler function
    :param f:
    :return:
    """

    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        converted_data = cast(CallbackDataType, update.callback_query.data)
        return await f(update, context, converted_data)

    return wrapped


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