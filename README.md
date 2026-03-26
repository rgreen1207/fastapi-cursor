# fastapi-cursor

Cursor/keyset pagination for [SQLAlchemy](https://www.sqlalchemy.org/) 2.x `Select` statements, designed for [FastAPI](https://fastapi.tiangolo.com/).

## Features

- **Keyset pagination** — stable, index-friendly, no `OFFSET` drift
- **HMAC-signed cursors** — tamper-proof opaque tokens passed as query params
- **Pluggable cursor stores**: in-process Memory or distributed Redis
- **LIMIT n+1** trick to cheaply detect next-page existence
- **Bring your own store** by subclassing `BaseCursorStore`

## Installation

```bash
# Core (includes MemoryStore)
pip install fastapi-cursor

# With Redis store
pip install fastapi-cursor[redis]
```

## Quick start

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi_cursor import CursorPaginator
from fastapi_cursor.backends import MemoryStore

app = FastAPI()
paginator = CursorPaginator(store=MemoryStore(), secret="change-me")

@app.get("/items")
async def list_items(
    cursor: str | None = None,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Item).order_by(Item.id)
    page = await paginator.paginate(session, stmt, cursor=cursor, page_size=page_size)
    return page
```

## Stores

| Store | Import | Extra |
|-------|--------|-------|
| Memory | `from fastapi_cursor.backends import MemoryStore` | built-in |
| Redis | `from fastapi_cursor.backends import RedisStore` | `pip install fastapi-cursor[redis]` |

## Custom store

```python
from fastapi_cursor.backends import BaseCursorStore
from fastapi_cursor.cursor import CursorState

class MyStore(BaseCursorStore):
    async def get(self, cursor_id: str) -> CursorState | None: ...
    async def set(self, cursor_id: str, state: CursorState, ttl: int) -> None: ...
    async def delete(self, cursor_id: str) -> None: ...
```

## Page response format

```json
{
  "items": [...],
  "next_cursor": "eyJ...",
  "prev_cursor": null,
  "has_next": true,
  "has_prev": false,
  "page_size": 20
}
```

## License

MIT
