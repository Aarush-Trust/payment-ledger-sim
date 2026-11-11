"""Shared test setup.

The app opens "sqlite:///./app.db" relative to the working directory and creates its tables when
main.py is imported. So every test run switches to a throwaway directory first, and the tracked
backend/app.db is never read or written.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def workdir(tmp_path_factory):
    path = tmp_path_factory.mktemp("ledger-db")
    previous = Path.cwd()
    os.chdir(path)
    yield path
    os.chdir(previous)


@pytest.fixture(scope="session")
def client(workdir):
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from fastapi.testclient import TestClient
    import main

    with TestClient(main.app) as test_client:
        yield test_client


def register_and_login(http, base_url=""):
    """Create a fresh user and return its Authorization header."""
    email = f"user-{uuid.uuid4().hex[:12]}@example.com"
    password = "correct-horse-battery"
    created = http.post(f"{base_url}/register", json={"email": email, "password": password})
    assert created.status_code == 201, created.text
    token = http.post(f"{base_url}/login", data={"username": email, "password": password})
    assert token.status_code == 200, token.text
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return register_and_login(client)
