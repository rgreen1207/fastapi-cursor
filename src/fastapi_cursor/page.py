from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Paginated response envelope.

    Attributes:
        items: The rows for this page.
        next_cursor: Opaque signed token to pass as ``cursor`` on the next
            request. ``None`` when this is the last page.
        prev_cursor: Reserved for bi-directional pagination; always ``None``
            in this version.
        has_next: Whether a next page exists.
        has_prev: Whether the client arrived here via a cursor (i.e. there
            are rows before this page).
        page_size: The requested page size.
    """

    items: list[Any]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_next: bool = False
    has_prev: bool = False
    page_size: int

    model_config = {"arbitrary_types_allowed": True}
