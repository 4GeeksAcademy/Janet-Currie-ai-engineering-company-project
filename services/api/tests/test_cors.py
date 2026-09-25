"""CORS origin configuration."""

from __future__ import annotations

import os
import unittest

from tests.helpers import client
from app.main import cors_origins, DEFAULT_CORS_ORIGINS


class CorsConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.get("CORS_ORIGINS")

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("CORS_ORIGINS", None)
        else:
            os.environ["CORS_ORIGINS"] = self._previous

    def test_default_origins_are_staff_ui(self) -> None:
        os.environ.pop("CORS_ORIGINS", None)
        self.assertEqual(cors_origins(), list(DEFAULT_CORS_ORIGINS))

    def test_parses_comma_separated_origins(self) -> None:
        os.environ["CORS_ORIGINS"] = "http://localhost:3001, http://127.0.0.1:3001"
        self.assertEqual(
            cors_origins(),
            ["http://localhost:3001", "http://127.0.0.1:3001"],
        )

    def test_options_from_staff_ui_is_allowed(self) -> None:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3001")
