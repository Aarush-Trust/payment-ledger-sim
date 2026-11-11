"""Regression test: 240 simultaneous same-key requests (30 rounds of 8).

Before the fix, about a third of these came back as HTTP 500, because the loser of each race hit the
unique constraint and the error was never caught. This runs a real uvicorn server (a separate
process, with real threads and real SQLite locking), not the in-process test client.

Pass criteria:
  - zero 5xx responses
  - zero duplicate rows (exactly one transaction per round)
  - every response in a round returns the same transaction
"""
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import httpx
import pytest

from conftest import register_and_login

BACKEND = Path(__file__).resolve().parents[1]
ROUNDS = 30
PER_ROUND = 8


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("ledger-server")  # the server's app.db lives here
    port = free_port()
    # Server output goes to a file, never a pipe: an unread pipe fills up (the unfixed code logs a
    # traceback per 500) and would block the server, hanging the test instead of failing it.
    log = open(workdir / "server.log", "wb")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--app-dir", str(BACKEND), "--port", str(port), "--log-level", "warning"],
        cwd=workdir,
        env={**os.environ, "PYTHONPATH": str(BACKEND)},
        stdout=log,
        stderr=log,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise RuntimeError("server did not start")
        yield base
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


def test_240_simultaneous_same_key_requests(server):
    with httpx.Client(timeout=30) as setup:
        auth = register_and_login(setup, server)

    status_codes = []
    per_round_ids = []
    errors = []

    for _ in range(ROUNDS):
        key = f"race-{uuid.uuid4()}"
        payload = {"amount": 5, "source_currency": "USD", "target_currency": "CAD", "idempotency_key": key}
        results = []
        barrier = threading.Barrier(PER_ROUND)

        def fire():
            try:
                with httpx.Client(timeout=30) as http:
                    barrier.wait()
                    r = http.post(f"{server}/transactions", headers=auth, json=payload)
                    results.append((r.status_code, r.json() if r.status_code < 500 else r.text))
            except Exception as exc:  # a dropped connection counts as a failure
                errors.append(repr(exc))

        threads = [threading.Thread(target=fire) for _ in range(PER_ROUND)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        status_codes += [code for code, _ in results]
        per_round_ids.append({body["id"] for code, body in results if code == 201})
        # Every response in the round carries the identical transaction.
        bodies = [body for code, body in results if code == 201]
        assert all(body == bodies[0] for body in bodies), f"responses differ within a round: {bodies}"

    assert not errors, errors[:3]
    assert len(status_codes) == ROUNDS * PER_ROUND == 240
    assert [c for c in status_codes if c >= 500] == [], "5xx responses: " + str(sorted(set(status_codes)))
    assert set(status_codes) == {201}
    assert all(len(ids) == 1 for ids in per_round_ids), "a round returned more than one transaction id"

    with httpx.Client(timeout=30) as http:
        rows = http.get(f"{server}/transactions", headers=auth).json()
    assert len(rows) == ROUNDS, f"expected {ROUNDS} rows (one per round), found {len(rows)}"
    assert len({row["id"] for row in rows}) == ROUNDS
    assert {row["id"] for ids in per_round_ids for row_id in ids for row in [{"id": row_id}]} == {row["id"] for row in rows}
