from contextlib import asynccontextmanager
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
import structlog

from src.settings import Settings

log = structlog.getLogger()


# Define your Custom classes for BotData, ChatData and UserData


class BotData:
    _db: async_sessionmaker[AsyncSession]
    _current_session: AsyncSession | None = None
    _settings: Settings


class ChatData:
    pass


ConversationState = TypeVar("ConversationState")


class UserData:
    _conversation_state: dict[type, Any] = {}

    def get_or_init_conversation_state(
        self, cls: Type[ConversationState]
    ) -> ConversationState:
        return self._conversation_state.setdefault(cls, cls())

    def clean_up_conversation_state(self, conversation_type: Type):
        if conversation_type in self._conversation_state:
            del self._conversation_state[conversation_type]


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property and utility methods here that interact with your context
    @asynccontextmanager
    async def session(self):
        if self.bot_data._current_session is not None:
            yield self.bot_data._current_session
        else:
            try:
                async with self.bot_data._db() as session:
                    self.bot_data._current_session = session
                    yield session
            finally:
                self.bot_data._current_session = None

    @property
    def settings(self) -> Settings:
        return self.bot_data._settings


context_types = ContextTypes(
    context=ApplicationContext, chat_data=ChatData, bot_data=BotData, user_data=UserData
)
