from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Select, asc, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from .backends.base import BaseCursorStore
from .backends.memory import MemoryStore
from .cursor import CursorState, CursorToken
from .page import Page


class CursorPaginator:
    """Cursor/keyset paginator for SQLAlchemy 2.x async queries.

    Args:
        store: A :class:`~fastapi_cursor.backends.base.BaseCursorStore`
            for persisting cursor state between requests. Defaults to
            :class:`~fastapi_cursor.backends.memory.MemoryStore`.
        secret: HMAC secret used to sign cursor tokens.
            **Change this in production.**
        default_page_size: Default rows per page when *page_size* is not
            passed to :meth:`paginate`.
        cursor_ttl: Seconds before a stored cursor expires.

    Basic usage::

        paginator = CursorPaginator(store=MemoryStore(), secret="my-secret")
        page = await paginator.paginate(session, select(Item).order_by(Item.id))
    """

    def __init__(
        self,
        store: Optional[BaseCursorStore] = None,
        secret: str = "change-me-in-production",
        default_page_size: int = 20,
        cursor_ttl: int = 300,
    ) -> None:
        self.store = store or MemoryStore()
        self._token = CursorToken(secret)
        self.default_page_size = default_page_size
        self.cursor_ttl = cursor_ttl

    async def paginate(
        self,
        session: AsyncSession,
        stmt: Select,
        *,
        cursor: Optional[str] = None,
        page_size: Optional[int] = None,
        sort_column: Optional[Any] = None,
        direction: str = "asc",
    ) -> Page:
        """Execute *stmt* with cursor-based keyset pagination.

        Args:
            session: SQLAlchemy async session.
            stmt: Base ``select()`` statement. Include an ``order_by`` clause
                or pass *sort_column*.
            cursor: Opaque token from a previous :class:`~fastapi_cursor.page.Page`.
                ``None`` (or omit) for the first page.
            page_size: Rows per page. Falls back to :attr:`default_page_size`.
            sort_column: SQLAlchemy column expression to ``ORDER BY``. Used only
                when the statement has no existing ``ORDER BY``.
            direction: ``"asc"`` or ``"desc"`` — used together with *sort_column*.

        Returns:
            A :class:`~fastapi_cursor.page.Page`.
        """
        size = page_size or self.default_page_size
        state: Optional[CursorState] = None
        has_prev = False

        if cursor is not None:
            try:
                cursor_id = self._token.decode(cursor)
                state = await self.store.get(cursor_id)
                has_prev = state is not None
            except (ValueError, Exception):
                state = None  # Invalid/expired cursor — fall back to first page

        # Apply sort column when provided
        if sort_column is not None:
            order_fn = asc if direction == "asc" else desc
            stmt = stmt.order_by(order_fn(sort_column))

        # Build keyset WHERE clause from cursor state
        paginated_stmt = stmt
        if state is not None:
            col = state.column
            val = state.value
            if state.direction == "asc":
                paginated_stmt = stmt.filter(
                    text(f"{col} > :cursor_val")
                ).params(cursor_val=val)
            else:
                paginated_stmt = stmt.filter(
                    text(f"{col} < :cursor_val")
                ).params(cursor_val=val)

        # LIMIT n+1 — the extra row tells us whether a next page exists.
        paginated_stmt = paginated_stmt.limit(size + 1)

        result = await session.execute(paginated_stmt)
        rows = result.all()

        has_next = len(rows) > size
        items = rows[:size]

        next_cursor_token: Optional[str] = None
        if has_next and items:
            last_row = items[-1]

            # Resolve column name and direction for the next cursor.
            if state is not None:
                col_name = state.column
                col_dir = state.direction
            elif sort_column is not None:
                col_name = sort_column.key
                col_dir = direction
            else:
                col_name = result.keys()[0]
                col_dir = "asc"

            # Extract the last value — supports ORM models and Core Row objects.
            if hasattr(last_row, "_mapping"):
                last_val = last_row._mapping[col_name]
            elif hasattr(last_row, col_name):
                last_val = getattr(last_row, col_name)
            else:
                last_val = last_row[0]

            new_state = CursorState(
                column=col_name,
                value=last_val,
                direction=col_dir,
                page_size=size,
            )
            new_id = str(uuid.uuid4())
            await self.store.set(new_id, new_state, ttl=self.cursor_ttl)
            next_cursor_token = self._token.encode(new_id)

        return Page(
            items=list(items),
            next_cursor=next_cursor_token,
            prev_cursor=None,
            has_next=has_next,
            has_prev=has_prev,
            page_size=size,
        )
