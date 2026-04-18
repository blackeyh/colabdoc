"""Shared pytest fixtures.

The real deployment runs on Postgres (Neon). For tests we stand up an
in-memory SQLite engine, override the `get_db` dependency, and share a single
connection so the schema survives across sessions. `JSONType` in
`database.py` already picks `JSON` on SQLite, so `create_all` works against
the test engine.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"

sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_MINUTES", "20")
os.environ.setdefault("JWT_REFRESH_DAYS", "7")
os.environ.setdefault("AI_PROVIDER", "null")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import database as db_module
import models
import main as app_module
from database import get_db


TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

# Point the module-level engine/session at the test DB. Anything that imports
# `SessionLocal` directly (e.g. the websocket handler in main.py) sees the
# same in-memory SQLite instead of trying to reach Neon.
db_module.engine = TEST_ENGINE
db_module.SessionLocal = TestingSessionLocal
app_module.SessionLocal = TestingSessionLocal
app_module.engine = TEST_ENGINE


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app_module.app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_schema():
    models.Base.metadata.drop_all(bind=TEST_ENGINE)
    models.Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    models.Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _register_and_login(client, name: str, email: str, password: str = "password123"):
    client.post("/auth/register", json={"name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "id": data["user"]["id"],
        "name": data["user"]["name"],
        "email": data["user"]["email"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest.fixture
def auth_user(client):
    return _register_and_login(client, "Alice", "alice@example.com")


@pytest.fixture
def auth_header(auth_user):
    return auth_user["headers"]


@pytest.fixture
def user_factory(client):
    counter = {"n": 0}

    def _make(name: str | None = None, email: str | None = None, password: str = "password123"):
        counter["n"] += 1
        n = counter["n"]
        return _register_and_login(
            client,
            name or f"User{n}",
            email or f"user{n}@example.com",
            password,
        )

    return _make


@pytest.fixture
def doc_factory(client, auth_user):
    def _make(title: str = "Doc", headers=None):
        r = client.post(
            "/documents",
            json={"title": title},
            headers=headers or auth_user["headers"],
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _make
