from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
# Postgres: SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://user:password@host:5432/dbname"

# Engine: connection to DB
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed only for SQLite
    pool_pre_ping=True,  # checks connections before using them
)

# Session Factory: short-term DB sessions upon request
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for ORM models
Base = declarative_base()