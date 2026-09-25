"""Pytest fixtures. Env and TestClient come from helpers (imported first)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.helpers import reset_auth_db
from app.cache import response_cache


@pytest.fixture(autouse=True)
def _isolated_auth_db() -> Iterator[None]:
    reset_auth_db()
    response_cache.clear()
    yield
    response_cache.clear()
