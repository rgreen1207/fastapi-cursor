from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..cursor import CursorState


class BaseCursorStore(ABC):
    """Abstract base class for cursor state storage backends.

    Implement :meth:`get`, :meth:`set`, and :meth:`delete` to integrate
    any storage system (Memcached, DynamoDB, etc.).

    All methods must be safe for concurrent async use.
    """

    @abstractmethod
    async def get(self, cursor_id: str) -> Optional[CursorState]:
        """Return :class:`CursorState` for *cursor_id*, or ``None`` if absent/expired."""

    @abstractmethod
    async def set(self, cursor_id: str, state: CursorState, ttl: int = 300) -> None:
        """Persist *state* under *cursor_id* with an expiry of *ttl* seconds."""

    @abstractmethod
    async def delete(self, cursor_id: str) -> None:
        """Remove *cursor_id* from the store. No-op if absent."""
