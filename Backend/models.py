"""
models.py — Root-level shim.
Re-exports everything from the database package so other modules
can simply do: from models import User, DATABASE_URL, etc.
"""
from database.connection import DATABASE_URL, SYNC_DATABASE_URL, get_sync_session, sync_engine, Base
from database.models import (
    User,
    StudentProfile,
    TestSession,
    ChatMessage,
    University,
    Program,
    Application,
    Scholarship,
    user_saved_programs,
    ApplicationStatus,
    TestType,
)
from database.init_db import push_schema as _push_schema


async def init_db():
    """Async schema push — call with await inside FastAPI startup."""
    await _push_schema()


def init_db_sync():
    """Sync wrapper — use this from CLI (main.py) only."""
    import asyncio
    asyncio.run(_push_schema())


__all__ = [
    "User", "StudentProfile", "TestSession", "ChatMessage",
    "University", "Program", "Application", "Scholarship",
    "user_saved_programs", "ApplicationStatus", "TestType",
    "DATABASE_URL", "SYNC_DATABASE_URL",
    "get_sync_session", "sync_engine", "Base",
    "init_db",
]
