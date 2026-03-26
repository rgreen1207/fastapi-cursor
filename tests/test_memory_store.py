import asyncio
import time
import pytest
from fastapi_cursor.backends.memory import MemoryStore
from fastapi_cursor.cursor import CursorState


@pytest.mark.asyncio
async def test_set_and_get():
    store = MemoryStore()
    state = CursorState(column="id", value=10, direction="asc", page_size=20)
    await store.set("cursor-1", state, ttl=60)
    retrieved = await store.get("cursor-1")
    assert retrieved is not None
    assert retrieved.column == "id"
    assert retrieved.value == 10
    assert retrieved.direction == "asc"
    assert retrieved.page_size == 20


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    store = MemoryStore()
    assert await store.get("nonexistent") is None


@pytest.mark.asyncio
async def test_delete():
    store = MemoryStore()
    state = CursorState(column="id", value=5)
    await store.set("cursor-del", state, ttl=60)
    await store.delete("cursor-del")
    assert await store.get("cursor-del") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_is_noop():
    store = MemoryStore()
    await store.delete("does-not-exist")  # must not raise


@pytest.mark.asyncio
async def test_ttl_expiry():
    store = MemoryStore()
    state = CursorState(column="id", value=1)
    await store.set("expiring", state, ttl=60)
    # Manually wind the clock forward past expiry
    async with store._lock:
        store._store["expiring"] = (state, time.monotonic() - 1)
    assert await store.get("expiring") is None


@pytest.mark.asyncio
async def test_multiple_concurrent_sets():
    store = MemoryStore()
    states = [CursorState(column="id", value=i) for i in range(10)]
    await asyncio.gather(*[store.set(f"c-{i}", s, ttl=60) for i, s in enumerate(states)])
    results = await asyncio.gather(*[store.get(f"c-{i}") for i in range(10)])
    assert all(r is not None for r in results)
    assert [r.value for r in results] == list(range(10))
