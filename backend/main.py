from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import User, Transaction
import schemas

# Create all tables on startup
Base.metadata.create_all(bind=engine)
app = FastAPI(title = "Payment Ledger Simulator")

# DB session dependency: one session per request
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Simple health endpoint
@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

# Debug endpoint to list users count
@app.get("/debug/users-count")
def users_count(db: Session = Depends(get_db)) -> dict:
    count = db.query(User).count()
    return {"users_count": count}

