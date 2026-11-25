"""Engine and session handling."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from database.models import Base


def make_engine(url: Optional[str] = None) -> Engine:
    url = url or settings.database_url
    kwargs = {}
    if url.startswith("sqlite"):
        # FastAPI handles requests in different threads; SQLite needs this flag.
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


engine = make_engine()
SessionLocal = make_session_factory(engine)


def init_db(bind: Optional[Engine] = None) -> None:
    """Create tables if they do not exist yet."""
    Base.metadata.create_all(bind or engine)


@contextmanager
def session_scope(factory: Optional[sessionmaker] = None) -> Iterator[Session]:
    """Commit on success, roll back on error, always close."""
    session = (factory or SessionLocal)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: `db: Session = Depends(get_db)`."""
    with session_scope() as session:
        yield session
