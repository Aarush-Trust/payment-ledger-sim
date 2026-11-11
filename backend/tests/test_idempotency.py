"""Retries with the same idempotency key replay the original transaction."""
import uuid
from concurrent.futures import ThreadPoolExecutor


def body(key):
    return {"amount": 100, "source_currency": "USD", "target_currency": "EUR", "idempotency_key": key}


def test_sequential_retry_returns_the_original_transaction(client, auth):
    key = f"k-{uuid.uuid4().hex}"
    first = client.post("/transactions", headers=auth, json=body(key))
    second = client.post("/transactions", headers=auth, json=body(key))
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert len(client.get("/transactions", headers=auth).json()) == 1


def test_same_key_for_different_users_is_independent(client):
    from conftest import register_and_login

    a, b = register_and_login(client), register_and_login(client)
    key = f"k-{uuid.uuid4().hex}"
    ra = client.post("/transactions", headers=a, json=body(key)).json()
    rb = client.post("/transactions", headers=b, json=body(key)).json()
    assert ra["id"] != rb["id"]


def test_losing_a_race_replays_the_winner_instead_of_a_500(client, auth):
    """Forces the exact race: the lookup finds nothing, then another request commits first.

    The first lookup is made to miss, as it would for a request that started before the winner
    committed. The insert then violates the unique constraint. The endpoint must roll back and
    return the winner's transaction.
    """
    import main

    key = f"k-{uuid.uuid4().hex}"
    winner = client.post("/transactions", headers=auth, json=body(key)).json()

    real_lookup = main.find_existing_transaction
    calls = {"n": 0}

    def lookup_misses_first_time(db, user_id, idempotency_key):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_lookup(db, user_id, idempotency_key)

    main.find_existing_transaction = lookup_misses_first_time
    try:
        loser = client.post("/transactions", headers=auth, json=body(key))
    finally:
        main.find_existing_transaction = real_lookup

    assert calls["n"] == 2, "the endpoint should look the transaction up again after the rollback"
    assert loser.status_code == 201
    assert loser.json() == winner
    assert len(client.get("/transactions", headers=auth).json()) == 1


def test_session_is_usable_after_the_rollback(client, auth):
    """After a replayed duplicate, the same user can still write new transactions."""
    key = f"k-{uuid.uuid4().hex}"
    client.post("/transactions", headers=auth, json=body(key))
    client.post("/transactions", headers=auth, json=body(key))
    fresh = client.post("/transactions", headers=auth, json=body(f"k-{uuid.uuid4().hex}"))
    assert fresh.status_code == 201
    assert len(client.get("/transactions", headers=auth).json()) == 2


def test_threaded_duplicates_in_process(client, auth):
    key = f"k-{uuid.uuid4().hex}"
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: client.post("/transactions", headers=auth, json=body(key)), range(16)))
    assert [r.status_code for r in responses].count(500) == 0
    assert len({r.json()["id"] for r in responses}) == 1
    assert len(client.get("/transactions", headers=auth).json()) == 1
