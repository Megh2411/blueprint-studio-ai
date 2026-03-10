import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Prefer pydantic-loaded settings (which reads .env) but fall back to os.environ.
db_url = getattr(settings, "DATABASE_URL", None) or os.environ.get("DATABASE_URL")

if not db_url:
    raise ValueError("DATABASE_URL is not set. Supabase database connection is required.")

engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ---> The function we just added back! <---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    try:
        print("Connecting to Supabase via transaction pooler...")
        with engine.connect() as connection:
            print("Successfully connected to Supabase!")
    except Exception as e:
        print(f"Connection failed: {e}")