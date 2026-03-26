"""Tests for CursorPaginator using in-memory SQLite via aiosqlite."""
import pytest

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

pytestmark = pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite not installed")

from sqlalchemy import select, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fastapi_cursor import CursorPaginator
from fastapi_cursor.backends.memory import MemoryStore


class Base(DeclarativeBase):
    pass


class Widget(Base):
    __tablename__ = "widgets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


@pytest.fixture
async def widget_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        from sqlalchemy import insert
        await session.execute(
            insert(Widget),
            [{"id": i, "name": f"widget-{i:03d}"} for i in range(1, 26)],
        )
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_first_page_no_cursor(widget_session):
    paginator = CursorPaginator(store=MemoryStore(), secret="test")
    stmt = select(Widget).order_by(Widget.id)
    page = await paginator.paginate(widget_session, stmt, page_size=10)

    assert len(page.items) == 10
    assert page.has_next is True
    assert page.next_cursor is not None
    assert page.has_prev is False


@pytest.mark.asyncio
async def test_second_page_with_cursor(widget_session):
    paginator = CursorPaginator(store=MemoryStore(), secret="test")
    stmt = select(Widget).order_by(Widget.id)

    page1 = await paginator.paginate(widget_session, stmt, page_size=10)
    page2 = await paginator.paginate(
        widget_session, stmt, cursor=page1.next_cursor, page_size=10
    )

    assert len(page2.items) == 10
    assert page2.has_prev is True
    # Verify non-overlapping: last id of page1 < first id of page2
    last_id_p1 = page1.items[-1].id
    first_id_p2 = page2.items[0].id
    assert first_id_p2 > last_id_p1


@pytest.mark.asyncio
async def test_last_page_has_no_next(widget_session):
    paginator = CursorPaginator(store=MemoryStore(), secret="test")
    stmt = select(Widget).order_by(Widget.id)

    # 25 widgets, page_size=10 → pages of 10, 10, 5
    page1 = await paginator.paginate(widget_session, stmt, page_size=10)
    page2 = await paginator.paginate(
        widget_session, stmt, cursor=page1.next_cursor, page_size=10
    )
    page3 = await paginator.paginate(
        widget_session, stmt, cursor=page2.next_cursor, page_size=10
    )

    assert len(page3.items) == 5
    assert page3.has_next is False
    assert page3.next_cursor is None


@pytest.mark.asyncio
async def test_invalid_cursor_falls_back_to_first_page(widget_session):
    paginator = CursorPaginator(store=MemoryStore(), secret="test")
    stmt = select(Widget).order_by(Widget.id)
    page = await paginator.paginate(
        widget_session, stmt, cursor="invalid-garbage", page_size=10
    )
    assert len(page.items) == 10
    assert page.has_prev is False


@pytest.mark.asyncio
async def test_page_size_respected(widget_session):
    paginator = CursorPaginator(store=MemoryStore(), secret="test")
    stmt = select(Widget).order_by(Widget.id)
    page = await paginator.paginate(widget_session, stmt, page_size=5)
    assert len(page.items) == 5


@pytest.mark.asyncio
async def test_all_items_covered_across_pages(widget_session):
    """Paginating through all pages should yield every row exactly once."""
    paginator = CursorPaginator(store=MemoryStore(), secret="test")
    stmt = select(Widget).order_by(Widget.id)
    all_ids: list[int] = []
    cursor = None

    while True:
        page = await paginator.paginate(widget_session, stmt, cursor=cursor, page_size=7)
        all_ids.extend(row.id for row in page.items)
        if not page.has_next:
            break
        cursor = page.next_cursor

    assert all_ids == list(range(1, 26))
