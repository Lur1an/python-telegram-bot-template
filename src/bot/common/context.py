from typing import (
    TypeVar,
    Dict,
    Type,
    Any,
)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from telegram.ext import (
    CallbackContext,
    ExtBot,
    ContextTypes,
)
import logging

from src.settings import Settings
log = logging.getLogger(__name__)


# Define your Custom classes for BotData, ChatData and UserData


class BotData:
    _db: async_sessionmaker[AsyncSession]
    _settings: Settings
    

class ChatData:
    pass


ConversationState = TypeVar("ConversationState")

class UserData:
    _conversation_state: Dict[type, Any] = {}

    def get_or_init_conversation_state(self, cls: Type[ConversationState]) -> ConversationState:
        return self._conversation_state.setdefault(cls, cls())

    def clean_up_conversation_state(self, conversation_type: Type):
        if conversation_type in self._conversation_state:
            del self._conversation_state[conversation_type]


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property and utility methods here that interact with your context
    @property
    def session(self) -> async_sessionmaker[AsyncSession]:
        return self.bot_data._db

    @property
    def settings(self) -> Settings:
        return self.bot_data._settings


context_types = ContextTypes(
    context=ApplicationContext, chat_data=ChatData, bot_data=BotData, user_data=UserData
)
