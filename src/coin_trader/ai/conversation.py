"""AI conversation management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class Conversation:
    """Manages conversation history for AI interactions."""

    messages: List[Message] = field(default_factory=list)
    max_history: int = 20

    def add_system(self, content: str) -> None:
        # Only keep one system message
        self.messages = [m for m in self.messages if m.role != "system"]
        self.messages.insert(0, Message(role="system", content=content))

    def add_user(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))
        self._trim()

    def add_assistant(self, content: str) -> None:
        self.messages.append(Message(role="assistant", content=content))
        self._trim()

    def to_api_format(self) -> List[Dict[str, str]]:
        """Convert to API-compatible message format."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def get_system_message(self) -> str:
        for m in self.messages:
            if m.role == "system":
                return m.content
        return ""

    def get_non_system_messages(self) -> List[Dict[str, str]]:
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
            if m.role != "system"
        ]

    def _trim(self) -> None:
        """Keep conversation within max_history."""
        non_system = [m for m in self.messages if m.role != "system"]
        system = [m for m in self.messages if m.role == "system"]
        if len(non_system) > self.max_history:
            non_system = non_system[-self.max_history:]
        self.messages = system + non_system

    def clear(self) -> None:
        system = [m for m in self.messages if m.role == "system"]
        self.messages = system
