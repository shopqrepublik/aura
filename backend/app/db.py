"""
SQLAlchemy engine/session against Supabase Postgres. DATABASE_URL is the
Session Pooler connection string from Supabase's Database settings (port
5432 -- suits a long-running Fly.io process, not the Transaction pooler
meant for serverless/many-short-lived-connections use cases).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")

# None when DATABASE_URL is unset (e.g. local UI-only dev without a .env) --
# get_db() below turns that into a clear 503 instead of a confusing crash at
# import time, same "degrade, don't crash" convention as OPENAI_API_KEY.
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def get_db():
    if SessionLocal is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="database not configured (DATABASE_URL missing)")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
