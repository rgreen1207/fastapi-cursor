from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING

from .base import BaseCursorStore
from ..cursor import CursorState

if TYPE_CHECKING:
    import aioredis

_KEY_PREFIX = "fastapi_cursor:"


class RedisStore(BaseCursorStore):
    """Cursor store backed by Redis. Suitable for multi-instance deployments.

    Install with: ``pip install fastapi-cursor[redis]``
    """

    def __init__(
        self,
        url: str = "redis://localhost",
        key_prefix: str = _KEY_PREFIX,
    ) -> None:
        self.url = url
        self.key_prefix = key_prefix
        self._redis: "aioredis.Redis | None" = None

    async def _get_redis(self) -> "aioredis.Redis":
        if self._redis is None:
            try:
                import aioredis
            except ImportError as exc:
                raise ImportError(
                    "Install fastapi-cursor[redis] to use RedisStore."
                ) from exc
            self._redis = await aioredis.from_url(self.url, decode_responses=True)
        return self._redis

    def _key(self, cursor_id: str) -> str:
        return f"{self.key_prefix}{cursor_id}"

    async def get(self, cursor_id: str) -> Optional[CursorState]:
        redis = await self._get_redis()
        raw = await redis.get(self._key(cursor_id))
        if raw is None:
            return None
        return CursorState.from_dict(json.loads(raw))

    async def set(self, cursor_id: str, state: CursorState, ttl: int = 300) -> None:
        redis = await self._get_redis()
        await redis.set(
            self._key(cursor_id),
            json.dumps(state.to_dict()),
            ex=ttl,
        )

    async def delete(self, cursor_id: str) -> None:
        redis = await self._get_redis()
        await redis.delete(self._key(cursor_id))

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
