from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class that all database models inherit from."""


@lru_cache
def get_engine():
    """Create the database engine once, on first use."""
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db():
    """Give one database session per request, and always close it."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()