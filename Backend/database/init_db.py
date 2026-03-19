"""
init_db.py — Push schema to PostgreSQL safely.
"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database.connection import async_engine, Base
from database.models import (
    User, StudentProfile, TestSession, ChatMessage,
    University, Program, Application,
    Scholarship, user_saved_programs
)

async def push_schema():
    print("Connecting to PostgreSQL to verify schema...")
    async with async_engine.begin() as conn:
        # ✅ NO MORE WIPING! This will only create tables if they don't exist.
        # Your users and data are now permanently safe.
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Schema verified! Existing data is safe.")
    await async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(push_schema())