from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator

from fastapi import HTTPException
from groq import APIStatusError, AsyncGroq, RateLimitError

from app.config import Settings, get_settings, read_groq_api_key
from app.core.groq_availability import GroqAvailability
from app.core.providers import (
    BaseChatProvider,
    build_groq_rate_limit_detail,
    build_groq_unavailable_detail,
)

logger = logging.getLogger(__name__)


def _to_groq_messages(messages: Any) -> list[dict[str, str]]:
    role_map = {
        "system": "system",
        "human": "user",
        "user": "user",
        "assistant": "assistant",
        "ai": "assistant",
    }
    groq_messages: list[dict[str, str]] = []
    for item in messages:
        if isinstance(item, dict):
            role = role_map.get(str(item.get("role", "user")), "user")
            content = str(item.get("content", ""))
        else:
            role_key, content = item[0], item[1]
            role = role_map.get(str(role_key), "user")
            content = str(content)
        if content:
            groq_messages.append({"role": role, "content": content})
    return groq_messages


class GroqChatProvider(BaseChatProvider):
    def __init__(self, settings: Settings, availability: GroqAvailability) -> None:
        self._settings = settings
        self._availability = availability
        self._client: AsyncGroq | None = None
        self._client_api_key: str | None = None

    def _get_client(self) -> AsyncGroq:
        api_key = read_groq_api_key()
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(get_settings()),
            )
        if self._client is None or self._client_api_key != api_key:
            self._client = AsyncGroq(api_key=api_key)
            self._client_api_key = api_key
        return self._client

    async def astream(self, messages: Any) -> AsyncGenerator[str, None]:
        await self._availability.require_available()
        groq_messages = _to_groq_messages(messages)

        try:
            stream = await self._get_client().chat.completions.create(
                model=get_settings().groq_chat_model,
                messages=groq_messages,
                stream=True,
                temperature=0,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except RateLimitError as exc:
            logger.warning("Groq rate limit: %s", exc)
            raise HTTPException(
                status_code=429,
                detail=build_groq_rate_limit_detail(),
            ) from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail=build_groq_rate_limit_detail(),
                ) from exc
            logger.warning("Groq API error: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(self._settings),
            ) from exc
        except HTTPException:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Groq chat streaming failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(self._settings),
            ) from exc
