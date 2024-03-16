from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from telegram import Update
from telegram.ext import BaseHandler, ConversationHandler


@dataclass(slots=True)
class ConversationBuilder:
    per_user: bool = True
    per_chat: bool = True
    per_message: bool = False
    allow_reentry: bool = False
    name: str | None = None
    persistent: bool = False
    conversation_timeout: float | timedelta | None = None
    map_to_parent: dict[object, object] | None = None
    states: dict = field(default_factory=dict)
    fallbacks: list = field(default_factory=list)
    entry_points: list = field(default_factory=list)

    def state(self, state):
        def decorator(handler: BaseHandler[Update, Any]):
            self.states.setdefault(state, list()).append(handler)

        return decorator

    def entry_point(self, handler: BaseHandler[Update, Any]):
        self.entry_points.append(handler)

    def fallback(self, handler: BaseHandler[Update, Any]):
        self.fallbacks.append(handler)

    def build(self):
        if not self.states:
            raise ValueError("Satet must be defined for ConversationHandler")
        if not self.entry_points:
            raise ValueError("Entry points must be defined for ConversationHandler")
        return ConversationHandler(
            entry_points=self.entry_points,
            states=self.states,
            fallbacks=self.fallbacks,
            per_user=self.per_user,
            per_chat=self.per_chat,
            per_message=self.per_message,
            conversation_timeout=self.conversation_timeout,
            allow_reentry=self.allow_reentry,
            name=self.name,
            persistent=self.persistent,
            map_to_parent=self.map_to_parent,
        )
