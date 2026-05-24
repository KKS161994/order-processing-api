from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.environment == "development",
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Session:
    """FastAPI dependency for database session"""
    with SessionLocal() as db:
        try:
            yield db
            db.commit()       # success path — one commit for the whole request
        except Exception:
            db.rollback()     # any error anywhere — single rollback
            raise