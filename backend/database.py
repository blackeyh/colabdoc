from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import require_env


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _normalize_database_url(require_env("DATABASE_URL"))

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Dialect-aware JSON column type. Postgres gets JSONB (indexable, validated);
# SQLite falls back to plain JSON so the test fixture can stand up schemas
# without a Postgres server. Models should import JSONType from here, not
# from sqlalchemy.dialects.postgresql directly.
JSONType = JSONB().with_variant(JSON(), "sqlite")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
