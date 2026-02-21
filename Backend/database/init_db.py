"""
init_db.py — Push schema to PostgreSQL.
Run directly:  python -m database.init_db
"""
import asyncio
import sys
import os

# Make sure Backend/ is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database.connection import async_engine, Base

# Import ALL models so SQLAlchemy registers them with Base.metadata
from database.models import (
    User, StudentProfile, TestSession,
    University, Program, Application,
    Scholarship, user_saved_programs
)


async def push_schema():
    print("Connecting to PostgreSQL...")

    tables = list(Base.metadata.tables.keys())
    print(f"Tables detected: {tables}")

    if not tables:
        print("ERROR: No tables detected. Make sure all models are imported.")
        return

    async with async_engine.begin() as conn:
        print("Pushing schema...")
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Schema pushed successfully!")
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(push_schema())
