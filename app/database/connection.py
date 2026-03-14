import os
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
