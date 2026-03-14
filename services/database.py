from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Engine — created once at import time, reused for the life of the process
# ---------------------------------------------------------------------------

def _make_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_async_engine(
        url,
        pool_size=5,          # max persistent connections
        max_overflow=10,      # extra connections allowed under load
        pool_pre_ping=True,   # test connections before use (handles DB restarts)
        echo=False,           # set True temporarily to log all SQL for debugging
    )


engine = _make_engine()

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # keep objects usable after commit
)


# ---------------------------------------------------------------------------
# Base class for ORM models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Session context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Usage:
        async with get_db() as db:
            result = await db.execute(select(UserORM))

    Automatically commits on success, rolls back on exception.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    """Call on shutdown to release all DB connections cleanly."""
    await engine.dispose()