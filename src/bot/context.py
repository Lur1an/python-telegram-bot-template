from typing import Iterable

from telegram.ext import CallbackContext, ExtBot, ContextTypes


# Define your Custom classes for BotData, ChatData and UserData

class BotData:
    pass


class ChatData:
    pass


class UserData:
    pass


class ApplicationContext(CallbackContext[ExtBot, UserData, ChatData, BotData]):
    # Define custom @property methods here
    pass
