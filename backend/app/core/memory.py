from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import BaseMessage


SESSION_TTL_SECONDS = 2 * 60 * 60
MEMORY_WINDOW_K = 10


@dataclass
class _SessionEntry:
    memory: ConversationBufferWindowMemory
    last_accessed: float


class MemoryManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, _SessionEntry] = {}

    def _evict_stale(self) -> None:
        now = time.time()
        stale = [
            session_id
            for session_id, entry in self._sessions.items()
            if now - entry.last_accessed > SESSION_TTL_SECONDS
        ]
        for session_id in stale:
            del self._sessions[session_id]

    def get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        self._evict_stale()
        now = time.time()
        entry = self._sessions.get(session_id)
        if entry is None:
            entry = _SessionEntry(
                memory=ConversationBufferWindowMemory(
                    k=MEMORY_WINDOW_K,
                    return_messages=True,
                ),
                last_accessed=now,
            )
            self._sessions[session_id] = entry
        else:
            entry.last_accessed = now
        return entry.memory

    def get_history_messages(self, session_id: str) -> List[BaseMessage]:
        memory = self.get_memory(session_id)
        messages = memory.chat_memory.messages
        return list(messages)

    def append_exchange(self, session_id: str, question: str, answer: str) -> None:
        memory = self.get_memory(session_id)
        memory.chat_memory.add_user_message(question)
        memory.chat_memory.add_ai_message(answer)

    def clear_memory(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        self._evict_stale()
        return list(self._sessions.keys())
