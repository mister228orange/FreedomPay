from __future__ import annotations

import os
from pathlib import Path

import pytest

# Isolate test DB before app.engine is created on first import of app.db
_TEST_DB = Path(__file__).resolve().parent / "_test_freedompay.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
# Avoid embedding Taskiq scheduler under TestClient
os.environ["TASKIQ_EMBEDDED"] = "false"


@pytest.fixture()
def client(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.db import init_db
    from app.main import app

    monkeypatch.setattr(settings, "MERCHANT_WEBHOOK_URL", "")
    init_db()
    with TestClient(app) as c:
        yield c
