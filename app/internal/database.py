import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    """
    FastAPI-style dependency for getting a DB session.
    Not currently used in WebSocket handlers (they create sessions manually),
    but available for future REST endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


