import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

load_dotenv()

# .env uses DATABASE_URI
DATABASE_URL = os.getenv("DATABASE_URI")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URI not found in .env file!")

# --- Async Engine (for FastAPI / async code) ---
async_engine = create_async_engine(
    DATABASE_URL,
    connect_args={"statement_cache_size": 0},
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# --- Sync Engine (for CLI / sync code like modules) ---
# Strip +asyncpg to get a sync-compatible URL (uses psycopg2)
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(bind=sync_engine)

def get_sync_session():
    """Returns a new sync SQLAlchemy session."""
    return SyncSessionLocal()


class Base(DeclarativeBase):
    pass
