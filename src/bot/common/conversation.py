from functools import wraps
from typing import (
    TypeVar,
    cast,
)
from telegram import Update
from telegram.ext import (
    ConversationHandler,
)
import logging
from src.bot.common.context import ApplicationContext, UserData

log = logging.getLogger(__name__)

ConversationState = TypeVar("ConversationState")


def init_stateful_conversation(conversation_state_type: type, inject: bool = True):
    def inner_decorator(f):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            user_data = context.user_data
            assert user_data
            user_data.initialize_conversation_state(conversation_state_type)
            if inject:
                state = user_data.get_conversation_state(conversation_state_type)
                return await f(update, context, state)
            else:
                return await f(update, context)

        return wrapped

    return inner_decorator


def inject_conversation_state(conversation_state_type: type):
    def inner_decorator(f):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            state = context.user_data.get_conversation_state(conversation_state_type)  # type: ignore
            return await f(update, context, state)

        return wrapped

    return inner_decorator


def cleanup_stateful_conversation(conversation_state_type: type, inject: bool = True):
    """
    Cleans up the user_data dict field that was holding onto the stateful conversation object and returns ConversationHandler.END,
    exceptions are ignored to ensure that the conversation state is cleaned up and the handlers ends
    """

    def inner_decorator(f):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            user_data = cast(UserData, context.user_data)
            try:
                if inject:
                    result = await f(
                        update,
                        context,
                        user_data.get_conversation_state( 
                            conversation_state_type
                        ),
                    )
                else:
                    result = await f(update, context)
            except Exception as e:
                log.warning(
                    f"Encountered exception during last step of conversation: {e}, ending conversation with User"
                )
                result = ConversationHandler.END
            finally:
                user_data.clean_up_conversation_state(conversation_state_type)
            return result

        return wrapped

    return inner_decorator
