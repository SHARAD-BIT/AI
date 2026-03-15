import os
import sqlite3
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


def _build_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tender_rag.db")

engine = create_engine(
    DATABASE_URL,
    connect_args=_build_connect_args(DATABASE_URL),
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    # Import models here so SQLAlchemy registers them before create_all.
    from app.models import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def vacuum_sqlite_database() -> bool:
    if not DATABASE_URL.startswith("sqlite:///"):
        return False

    database_path = DATABASE_URL.removeprefix("sqlite:///")
    if not database_path or database_path == ":memory:":
        return False

    database_path = os.path.abspath(database_path)
    if not os.path.exists(database_path):
        return False

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        connection.execute("VACUUM;")
        connection.commit()
    finally:
        connection.close()

    return True
