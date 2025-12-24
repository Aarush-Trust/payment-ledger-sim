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

cd backend
pipenv install
pipenv shell
uvicorn main:app --reload

Then open `http://127.0.0.1:8000/docs` for interactive API docs.
