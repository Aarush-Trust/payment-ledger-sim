# Payment Ledger Simulator

A small full-stack project that simulates cross-border payments with a simple ledger.

## Features

- User registration and login with hashed passwords (argon2).
- JWT-based auth; protected endpoints for all payment operations.
- Per-user transaction ledger with idempotent payment creation.
- Deterministic FX conversion (USD/EUR/BTC) with stored rate and converted amount.
- Simple risk scoring (`LOW` / `MEDIUM` / `HIGH`) based on transaction size.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic, argon2 (via passlib), pipenv.
- Database: SQLite for development (designed to swap to PostgreSQL later).
- Auth: OAuth2 password flow with JWT access tokens.

## Running locally
```
cd backend
pipenv install
pipenv shell
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for interactive API docs.

## Behaviour worth knowing

- **Retries are safe.** A `POST /transactions` with an `idempotency_key` you have already used returns the original transaction (same status, same body). That holds when duplicates arrive at the same moment too: the unique constraint on `(user_id, idempotency_key)` rejects the loser's insert, which rolls back and replays the winner's transaction.
- **Unknown currency pairs are rejected.** A pair that is not in the rate table (for example CAD to EUR, or anything involving an unlisted currency) returns `422` with `{"detail": "Unsupported currency pair: ..."}`. Nothing is written, and the same idempotency key can be reused with a supported pair.

## Tests

```
cd backend
pipenv run pip install -r tests/requirements.txt
pipenv run pytest tests
```

The tests run in a temporary directory and never touch `backend/app.db`. `test_concurrent_duplicates.py` starts a real server and sends 240 simultaneous same-key requests (30 rounds of 8). It asserts zero 5xx responses, exactly one row per round, and an identical response body for every request in a round.
