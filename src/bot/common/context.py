from functools import wraps
from typing import Iterable, TypeVar, Dict, Generic, Type, Callable, Awaitable, Any

from telegram import Update
from telegram.ext import CallbackContext, ExtBot, ContextTypes, ConversationHandler
import logging

log = logging.getLogger(__name__)


# Define your Custom classes for BotData, ChatData and UserData

class BotData:
    pass


class ChatData:
    pass


ConversationState = TypeVar("ConversationState")


class UserData:
    _conversation_state: Dict[Type[ConversationState], ConversationState] = {}

    def get_conversation_state(self, cls: Type[ConversationState]) -> ConversationState:
        return self._conversation_state[cls]

    def initialize_conversation_state(self, cls: Type[ConversationState]):
        self._conversation_state[cls] = cls()

    def clean_up_conversation_state(self, conversation_type: Type[ConversationState]):
        del self._conversation_state[conversation_type]


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property methods here that interact with your context
    pass


context_types = ContextTypes(
    context=ApplicationContext,
    chat_data=ChatData,
    bot_data=BotData,
    user_data=UserData
)


def init_stateful_conversation(conversation_state_type: Type[ConversationState]):
    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            context.user_data.initialize_conversation_state(conversation_state_type)
            return await f(update, context)

        return wrapped

    return inner_decorator


def cleanup_stateful_conversation(conversation_state_type: Type[ConversationState]):
    """
    Cleans up the user_data dict field that was holding onto the stateful conversation object and returns ConversationHandler.END,
    exceptions are ignored to ensure that the conversation state is cleaned up and the handlers ends
    """

    def inner_decorator(f: Callable[[Update, ApplicationContext], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            try:
                await f(update, context)
            except Exception as e:
                log.warning(f"Encountered exception during last step of conversation: {e}")
            finally:
                context.user_data.clean_up_conversation_state(conversation_state_type)
                return ConversationHandler.END

        return wrapped

    return inner_decorator
