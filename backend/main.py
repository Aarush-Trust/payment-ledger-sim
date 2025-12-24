from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from collections.abc import Generator

from database import Base, engine, SessionLocal
from models import User, Transaction
import schemas
from conversion import convert
from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

# Create all tables on startup
Base.metadata.create_all(bind=engine)
app = FastAPI(title = "Payment Ledger Simulator")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# DB session dependency: one session per request
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Current User Details
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token_data = decode_access_token(token)
    if token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Simple health endpoint
@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

# User Registration
@app.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return schemas.Token(access_token=access_token)

# Debug endpoint to list users count
@app.get("/debug/users-count")
def users_count(db: Session = Depends(get_db)) -> dict:
    count = db.query(User).count()
    return {"users_count": count}

# Check transactions
@app.post(
    "/transactions",
    response_model=schemas.TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    tx_in: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check for existing transaction with same idempotency key for this user
    existing = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.idempotency_key == tx_in.idempotency_key,
        )
        .first()
    )
    if existing:
        # Idempotent behavior: return the already-created transaction
        return existing

    rate, converted = convert(tx_in.amount, tx_in.source_currency, tx_in.target_currency)
    tx = Transaction(
        user_id=current_user.id,
        amount=tx_in.amount,
        source_currency=tx_in.source_currency.upper(),
        target_currency=tx_in.target_currency.upper(),
        rate=rate,
        converted_amount=converted,
        idempotency_key=tx_in.idempotency_key,
        status="COMPLETED",
        # audit_hash could later be a hash of fields
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@app.get(
    "/transactions",
    response_model=list[schemas.TransactionRead],
)
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return txs