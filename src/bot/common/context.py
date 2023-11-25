from typing import (
    TypeVar,
    Dict,
    Type,
    Any,
)

from telegram.ext import (
    CallbackContext,
    ExtBot,
    ContextTypes,
)
import logging
log = logging.getLogger(__name__)


# Define your Custom classes for BotData, ChatData and UserData


class BotData:
    pass

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
    pass


context_types = ContextTypes(
    context=ApplicationContext, chat_data=ChatData, bot_data=BotData, user_data=UserData
)
