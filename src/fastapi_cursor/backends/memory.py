from __future__ import annotations

import asyncio
import time
from typing import Optional

from .base import BaseCursorStore
from ..cursor import CursorState


class MemoryStore(BaseCursorStore):
    """In-process cursor store backed by a plain dict with TTL enforcement.

    Suitable for single-instance applications and testing. Expired entries
    are lazily evicted on the next :meth:`get` access.
    """

    def __init__(self) -> None:
        # cursor_id -> (state, expires_at monotonic timestamp)
        self._store: dict[str, tuple[CursorState, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, cursor_id: str) -> Optional[CursorState]:
        async with self._lock:
            entry = self._store.get(cursor_id)
            if entry is None:
                return None
            state, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[cursor_id]
                return None
            return state

    async def set(self, cursor_id: str, state: CursorState, ttl: int = 300) -> None:
        async with self._lock:
            self._store[cursor_id] = (state, time.monotonic() + ttl)

    async def delete(self, cursor_id: str) -> None:
        async with self._lock:
            self._store.pop(cursor_id, None)
