import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Uses Postgres if DATABASE_URL is set in .env (e.g. your Supabase connection
# string) — falls back to a local SQLite file if it's not set, so this still
# works without any setup for quick local testing.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hiremailer.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()