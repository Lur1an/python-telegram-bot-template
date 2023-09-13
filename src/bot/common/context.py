from typing import (
    TypeVar,
    Dict,
    Type,
    Any,
    Optional,
)

from telegram.ext import (
    CallbackContext,
    ExtBot,
    ContextTypes,
)
import logging

from src.settings import settings
from src.user.persistence import User

log = logging.getLogger(__name__)


# Define your Custom classes for BotData, ChatData and UserData


class BotData:
    users: Dict[int, User] = {}


class ChatData:
    pass


ConversationState = TypeVar("ConversationState")


class UserData:
    _conversation_state: Dict[type, Any] = {}

    def get_conversation_state(self, cls: Type[ConversationState]) -> ConversationState:
        return self._conversation_state[cls]

    def initialize_conversation_state(self, cls: Type):
        self._conversation_state[cls] = cls()

    def clean_up_conversation_state(self, conversation_type: Type):
        if conversation_type in self._conversation_state:
            del self._conversation_state[conversation_type]


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property and utility methods here that interact with your context
    def get_cached_user(self, telegram_id: int) -> Optional[User]:
        if len(self.bot_data.users) >= settings.CACHE_LIMIT:
            keys = list(self.bot_data.users.keys())
            keys = keys[0 : min(int(settings.CACHE_LIMIT / 100), len(keys) - 1)]
            for key in keys:
                del self.bot_data.users[key]
        return self.bot_data.users.get(telegram_id, None)

    def cache_user(self, user: User):
        self.bot_data.users[user.telegram_id] = user


context_types = ContextTypes(
    context=ApplicationContext, chat_data=ChatData, bot_data=BotData, user_data=UserData
)
