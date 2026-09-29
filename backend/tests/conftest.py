# backend/tests/conftest.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        db_path=str(tmp_path / "test.db"),
        session_secret="test-secret",
        login_password="test-password",
    )


@pytest.fixture
def client(settings):
    app = create_app(settings, start_scheduler_job=False)
    return TestClient(app)
