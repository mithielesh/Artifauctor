# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# This creates a local SQLite file in your backend folder
SQLALCHEMY_DATABASE_URL = "sqlite:///./artifauctor.db"

# check_same_thread is set to False because FastAPI can access the DB from multiple worker threads
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to inject the database session into our API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()