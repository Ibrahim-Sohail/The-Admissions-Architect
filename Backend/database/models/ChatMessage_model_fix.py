"""
ADD THIS to your database/models.py — replace or update your existing ChatMessage class.

The `timestamp` column was missing, causing:
  "type object 'ChatMessage' has no attribute 'timestamp'"

After updating the model, run your DB migration / init_db() so the
column is actually created in the database.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid


class ChatMessage(Base):  # type: ignore  # Base is already defined in your database/models.py
    __tablename__ = "chat_messages"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role        = Column(String, nullable=False)       # "user" or "assistant"
    content     = Column(Text,   nullable=False)
    # ✅ THIS IS THE MISSING COLUMN — add it if it's not already in your model
    timestamp   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
