"""Auth flow: register, login, refresh, and access-vs-refresh separation."""

from datetime import datetime, timedelta

import pytest
from jose import jwt

import auth as auth_utils


def test_register_creates_user(client):
    r = client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "secret12"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "bob@example.com"
    assert body["name"] == "Bob"
    assert "id" in body


def test_register_duplicate_email_rejected(client):
    client.post(
        "/auth/register",
        json={"name": "A", "email": "dup@example.com", "password": "x" * 8},
    )
    r = client.post(
        "/auth/register",
        json={"name": "B", "email": "dup@example.com", "password": "x" * 8},
    )
    assert r.status_code == 400


def test_login_returns_access_and_refresh(client):
    client.post(
        "/auth/register",
        json={"name": "C", "email": "c@example.com", "password": "pw12345"},
    )
    r = client.post("/auth/login", json={"email": "c@example.com", "password": "pw12345"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]
    assert body["user"]["email"] == "c@example.com"


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"name": "D", "email": "d@example.com", "password": "pw12345"},
    )
    r = client.post("/auth/login", json={"email": "d@example.com", "password": "nope"})
    assert r.status_code == 401


def test_refresh_returns_new_tokens(client, auth_user):
    r = client.post(
        "/auth/refresh",
        json={"refresh_token": auth_user["refresh_token"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    # New access token should be usable
    r2 = client.get("/documents", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r2.status_code == 200


def test_refresh_rejects_access_token(client, auth_user):
    # Passing the access token where a refresh is expected must fail.
    r = client.post(
        "/auth/refresh",
        json={"refresh_token": auth_user["access_token"]},
    )
    assert r.status_code == 401


def test_protected_endpoint_rejects_refresh_as_access(client, auth_user):
    r = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {auth_user['refresh_token']}"},
    )
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/documents", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_expired_access_token_rejected(client, auth_user):
    expired = jwt.encode(
        {
            "sub": str(auth_user["id"]),
            "exp": datetime.utcnow() - timedelta(minutes=1),
            "type": "access",
        },
        auth_utils.JWT_SECRET,
        algorithm=auth_utils.JWT_ALGORITHM,
    )
    r = client.get("/documents", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
