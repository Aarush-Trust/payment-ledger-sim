from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import User, Transaction
import schemas
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