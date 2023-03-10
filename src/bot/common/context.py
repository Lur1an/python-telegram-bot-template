from functools import wraps
from typing import Iterable, TypeVar, Dict, Generic, Type, Callable, Awaitable, Any, Optional

from telegram import Update
from telegram.ext import CallbackContext, ExtBot, ContextTypes, ConversationHandler, CommandHandler
import logging

from src.user.persistence import User

log = logging.getLogger(__name__)


# Define your Custom classes for BotData, ChatData and UserData

class BotData:
    users: Dict[int, User] = {}


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
    # Define custom @property and utility methods here that interact with your context
    def get_cached_user(self, telegram_id: int) -> Optional[User]:
        return self.bot_data.users.get(telegram_id, None)

    def cache_user(self, user: User):
        self.bot_data.users[user.telegram_id] = user


context_types = ContextTypes(
    context=ApplicationContext,
    chat_data=ChatData,
    bot_data=BotData,
    user_data=UserData
)


def init_stateful_conversation(conversation_state_type: Type[ConversationState]):
    def inner_decorator(f: Callable[[Update, ApplicationContext, ConversationState], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            context.user_data.initialize_conversation_state(conversation_state_type)
            state = context.user_data.get_conversation_state(conversation_state_type)
            return await f(
                update,
                context,
                state
            )

        return wrapped

    return inner_decorator


def inject_conversation_state(conversation_state_type: Type[ConversationState]):
    def inner_decorator(f: Callable[[Update, ApplicationContext, ConversationState], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            state = context.user_data.get_conversation_state(conversation_state_type)
            return await f(update, context, state)

        return wrapped

    return inner_decorator


def cleanup_stateful_conversation(conversation_state_type: Type[ConversationState]):
    """
    Cleans up the user_data dict field that was holding onto the stateful conversation object and returns ConversationHandler.END,
    exceptions are ignored to ensure that the conversation state is cleaned up and the handlers ends
    """

    def inner_decorator(f: Callable[[Update, ApplicationContext, ConversationState], Awaitable[Any]]):
        @wraps(f)
        async def wrapped(update: Update, context: ApplicationContext):
            try:
                result = await f(
                    update,
                    context,
                    context.user_data.get_conversation_state(conversation_state_type)
                )
            except Exception as e:
                log.warning(
                    f"Encountered exception during last step of conversation: {e}, ending conversation with User"
                )
                result = ConversationHandler.END
            finally:
                context.user_data.clean_up_conversation_state(conversation_state_type)
            return result

        return wrapped

    return inner_decorator
