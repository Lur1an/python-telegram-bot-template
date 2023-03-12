from functools import wraps
from typing import Iterable, TypeVar, Dict, Generic, Type, Callable, Awaitable, Any

from telegram import Update
from telegram.ext import CallbackContext, ExtBot, ContextTypes


# Define your Custom classes for BotData, ChatData and UserData

class BotData:
    pass


class ChatData:
    p: str
    pass


ConversationState = TypeVar("ConversationState")


class UserData:
    _conversation_state = {}

    def get_conversation_state(self, cls: Type[ConversationState]) -> ConversationState:
        return self._conversation_state[cls]

    def initialize_conversation_state(self, cls: Type[ConversationState]):
        self._conversation_state[cls] = cls()

    def clean_up_conversation_state(self, cls: Type[ConversationState]):
        del self._conversation_state[cls]


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property methods here that interact with your context
    pass


def init_stateful_conversation(f: Callable[[Update, ApplicationContext], Awaitable[Any]],
                               conversation_state_type: Type[ConversationState]):
    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        context.user_data.initialize_conversation_state(conversation_state_type)
        return await f(update, context)

    return wrapped


def cleanup_stateful_conversation(f: Callable[[Update, ApplicationContext], Awaitable[Any]],
                                  conversation_state_type: Type[ConversationState]):
    """
    Cleans up the user_data dict field that was holding onto the stateful conversation object
    """

    @wraps(f)
    async def wrapped(update: Update, context: ApplicationContext):
        result = await f(update, context)
        context.user_data.clean_up_conversation_state(conversation_state_type)

    return wrapped
