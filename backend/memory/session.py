import json
import logging
import os
from collections import defaultdict
from typing import Any

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")


class SessionMemory:
    _fallback_messages: dict[str, list[str]] = defaultdict(list)
    _fallback_context: dict[str, str] = {}

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.prefix = f"session:{self.session_id}"
        self.ttl = 3600
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None
        self._redis_available: bool | None = None

    async def _can_use_redis(self) -> bool:
        if not self.redis_client:
            return False

        if self._redis_available is not None:
            return self._redis_available

        try:
            await self.redis_client.ping()
            self._redis_available = True
        except Exception as exc:
            self._redis_available = False
            logger.warning("Redis unavailable, using in-memory session storage: %s", exc)
        return self._redis_available

    async def get_context(self) -> dict[str, Any]:
        if await self._can_use_redis():
            data = await self.redis_client.get(f"{self.prefix}:context")
            return json.loads(data) if data else {}

        raw = self._fallback_context.get(self.session_id)
        return json.loads(raw) if raw else {}

    async def update_context(self, updates: dict[str, Any]):
        current = await self.get_context()
        current.update(updates)
        serialized = json.dumps(current)

        if await self._can_use_redis():
            await self.redis_client.setex(f"{self.prefix}:context", self.ttl, serialized)
            return

        self._fallback_context[self.session_id] = serialized

    async def clear(self):
        if await self._can_use_redis():
            await self.redis_client.delete(f"{self.prefix}:context")
            await self.redis_client.delete(f"{self.prefix}:messages")
            return

        self._fallback_context.pop(self.session_id, None)
        self._fallback_messages.pop(self.session_id, None)

    async def add_message(self, role: str, content: Any, **extra: Any):
        payload = {"role": role, "content": content, **extra}
        serialized = json.dumps(payload)

        if await self._can_use_redis():
            await self.redis_client.rpush(f"{self.prefix}:messages", serialized)
            await self.redis_client.expire(f"{self.prefix}:messages", self.ttl)
            return

        self._fallback_messages[self.session_id].append(serialized)
        self._fallback_messages[self.session_id] = self._fallback_messages[self.session_id][-50:]

    async def get_recent_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        if await self._can_use_redis():
            messages = await self.redis_client.lrange(f"{self.prefix}:messages", -limit, -1)
        else:
            messages = self._fallback_messages.get(self.session_id, [])[-limit:]

        return [json.loads(message) for message in messages]
