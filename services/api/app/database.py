"""SQLModel engine and session for inventory (separate from TinyDB)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

_API_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_API_ROOT / ".env")

_engine = None


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    sqlite_path = _API_ROOT / "data" / "inventory.sqlite"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{sqlite_path}"


def get_engine():
    global _engine
    if _engine is None:
        url = database_url()
        kwargs: dict = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
    return _engine


def reset_engine() -> None:
    """Test helper: drop the cached engine after DATABASE_URL changes."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_db() -> None:
    from app.inventory import models as _models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
