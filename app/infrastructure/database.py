from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://libsys:changeme@db:5432/libsysdb"
)


@lru_cache(maxsize=1)
def _get_engine():
    return create_async_engine(DATABASE_URL)


@lru_cache(maxsize=1)
def _get_session_local():
    return async_sessionmaker(
        bind=_get_engine(), class_=AsyncSession, expire_on_commit=False
    )


class _LazyEngine:
    """Proxy that delegates attribute access to the real engine on first use."""

    def __getattr__(self, name: str):
        return getattr(_get_engine(), name)


class _LazySessionLocal:
    """Proxy that delegates calls/attribute access to the real sessionmaker on first use."""

    def __call__(self, **kwargs):
        return _get_session_local()(**kwargs)

    def __getattr__(self, name: str):
        return getattr(_get_session_local(), name)


async_engine = _LazyEngine()  # type: ignore[assignment]
AsyncSessionLocal = _LazySessionLocal()  # type: ignore[assignment]


class Base(DeclarativeBase):
    pass
