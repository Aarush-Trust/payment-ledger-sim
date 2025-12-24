from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship: one user -> many transactions
    transactions = relationship("Transaction", back_populates="user")

class TransactionStatusEnum(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Money & Currency Information
    amount = Column(Float, nullable=False)
    source_currency = Column(String, nullable=False)
    target_currency = Column(String, nullable=False)

    # For idempotency and reconciliation
    idempotency_key = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Simple Audit Field
    audit_hash = Column(String, nullable=True)

    # Relationship back to User
    user = relationship("User", back_populates="transactions")

    __table_args__ = (
        # Prevent duplicate processing of the same logical payment
        UniqueConstraint("user_id", "idempotency_key", name="uq_user_id_idempotency_key"),
        # Common query patterns: by user, by created_at
        Index("ix_transactions_user_created_at", "user_id", "created_at"),
    )