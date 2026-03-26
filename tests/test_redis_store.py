"""Integration tests for RedisStore — skipped unless aioredis and Redis are available."""
import pytest

try:
    import aioredis
    HAS_AIOREDIS = True
except ImportError:
    HAS_AIOREDIS = False

pytestmark = pytest.mark.skipif(not HAS_AIOREDIS, reason="aioredis not installed")

REDIS_URL = "redis://localhost:6379"


async def _redis_available() -> bool:
    try:
        import aioredis
        r = await aioredis.from_url(REDIS_URL)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        return False


@pytest.fixture
async def redis_store():
    if not await _redis_available():
        pytest.skip("Redis not available")
    from fastapi_cursor.backends.redis import RedisStore
    store = RedisStore(url=REDIS_URL, key_prefix="test_fastapi_cursor:")
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_redis_set_get(redis_store):
    from fastapi_cursor.cursor import CursorState
    state = CursorState(column="id", value=99, direction="desc", page_size=15)
    await redis_store.set("r-cursor-1", state, ttl=60)
    retrieved = await redis_store.get("r-cursor-1")
    assert retrieved is not None
    assert retrieved.column == "id"
    assert retrieved.value == 99
    assert retrieved.direction == "desc"
    assert retrieved.page_size == 15


@pytest.mark.asyncio
async def test_redis_get_missing(redis_store):
    assert await redis_store.get("nonexistent-key-xyz-999") is None


@pytest.mark.asyncio
async def test_redis_delete(redis_store):
    from fastapi_cursor.cursor import CursorState
    state = CursorState(column="id", value=1)
    await redis_store.set("r-to-delete", state, ttl=60)
    await redis_store.delete("r-to-delete")
    assert await redis_store.get("r-to-delete") is None


@pytest.mark.asyncio
async def test_redis_store_close_idempotent(redis_store):
    await redis_store.close()
    await redis_store.close()  # must not raise
