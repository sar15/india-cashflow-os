"""
Database engine factory for Cashflow OS.

Reads DATABASE_URL from environment.  When the variable is absent the
application falls back to the legacy InMemoryStore so local development
remains zero-config.

Connection pool is kept small (max 5) to stay within Supabase free-tier
limits (~60 direct connections on the free plan).
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        db_path = Path(__file__).resolve().parents[3] / "data" / "cashflow.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def init_engine() -> Optional[Engine]:
    global _engine, _session_factory

    database_url = get_database_url()
    
    if database_url.startswith("sqlite"):
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    else:
        _engine = create_engine(
            database_url,
            pool_size=3,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "options": "-c search_path=cashflow,public",
            },
        )
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Optional[Engine]:
    return _engine


def get_session_factory() -> Optional[sessionmaker]:
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_database_available() -> bool:
    return _engine is not None


def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _session_factory = None


def health_check() -> bool:
    if _engine is None:
        return False
    try:
        with _engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
