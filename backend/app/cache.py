"""Redis-backed short-term memory, response cache and rate limiter (fakeredis in demo mode)."""

import hashlib
import json
import logging
import re
import time
from typing import Any

from app.config import Settings

logger = logging.getLogger("agentdesk.cache")


async def connect_redis(settings: Settings) -> tuple[Any, str]:
    if settings.redis_url:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        logger.info("Connected to Redis")
        return client, "redis"

    from fakeredis import FakeAsyncRedis, FakeServer

    logger.info("REDIS_URL not set - using in-memory fakeredis")
    return FakeAsyncRedis(server=FakeServer(), decode_responses=True), "in-memory (fakeredis)"


def normalize(message: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", "", message.lower()).split())


class Cache:
    """Three jobs: per-session conversation memory, FAQ response cache, fixed-window rate limit."""

    def __init__(self, redis: Any, kind: str, settings: Settings):
        self.r = redis
        self.kind = kind
        self.prefix = settings.redis_prefix
        self.memory_turns = settings.memory_turns
        self.cache_ttl_s = settings.cache_ttl_s
        self.rate_limit = settings.rate_limit_per_min

    def _k(self, *parts: str) -> str:
        return ":".join((self.prefix, *parts))

    # -- conversation memory -------------------------------------------------
    async def history(self, session_id: str) -> list[dict[str, str]]:
        raw = await self.r.lrange(self._k("mem", session_id), 0, -1)
        return [json.loads(x) for x in raw]

    async def remember(self, session_id: str, role: str, content: str) -> None:
        key = self._k("mem", session_id)
        await self.r.rpush(key, json.dumps({"role": role, "content": content}))
        await self.r.ltrim(key, -2 * self.memory_turns, -1)
        await self.r.expire(key, 3600)

    # -- response cache (stateless FAQ answers only) ---------------------------
    def _cache_key(self, message: str) -> str:
        return self._k("faq", hashlib.sha1(normalize(message).encode()).hexdigest())

    async def get_cached(self, message: str) -> dict | None:
        raw = await self.r.get(self._cache_key(message))
        return json.loads(raw) if raw else None

    async def set_cached(self, message: str, payload: dict) -> None:
        await self.r.set(self._cache_key(message), json.dumps(payload), ex=self.cache_ttl_s)

    # -- rate limiting ---------------------------------------------------------
    async def check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """Fixed one-minute window per client. Returns (allowed, retry_after_seconds)."""
        now = time.time()
        key = self._k("rl", client_id, str(int(now // 60)))
        count = await self.r.incr(key)
        if count == 1:
            await self.r.expire(key, 61)
        return count <= self.rate_limit, max(1, 60 - int(now % 60))

    async def close(self) -> None:
        try:
            await self.r.aclose()
        except Exception:  # pragma: no cover
            pass
