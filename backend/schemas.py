from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# ========== USER SCHEMAS ==========

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# ========== TRANSACTION SCHEMAS ==========

class TransactionBase(BaseModel):
    amount: float = Field(gt=0)
    source_currency: str
    target_currency: str

class TransactionCreate(TransactionBase):
    idempotency_key: str

class TransactionRead(TransactionBase):
    id: int
    status: str
    created_at: datetime
    audit_hash: Optional[str] = None

    class Config:
        orm_mode = True

class UserWithTransactions(UserRead):
    transactions: List[TransactionRead] = []

# Describes what /login returns
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"