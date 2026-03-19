"""
__init__.py — Central Database Models for Admission Architect.
"""
import enum
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base

# ==========================================
# Enums & Association Tables
# ==========================================

class TestType(enum.Enum):
    GRE = "GRE"
    IELTS = "IELTS"

class ApplicationStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

user_saved_programs = Table(
    'user_saved_programs',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id'), primary_key=True),
    Column('program_id', String, ForeignKey('programs.id'), primary_key=True)
)

# ==========================================
# Primary Models
# ==========================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)

    # Relationships
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    tests = relationship("TestSession", back_populates="user")
    chats = relationship("ChatMessage", back_populates="user")
    applications = relationship("Application", back_populates="user")
    saved_programs = relationship("Program", secondary=user_saved_programs)

class StudentProfile(Base):
    __tablename__ = "student_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    cgpa = Column(Float, nullable=True)
    gpa = Column(Float, nullable=True) # Legacy sync
    major_interest = Column(String, nullable=True)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    preferred_country = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")

class TestSession(Base):
    __tablename__ = "test_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    test_type = Column(Enum(TestType), nullable=False)
    module = Column(String, nullable=False)
    score_obtained = Column(Float, nullable=False)
    feedback = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="tests")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)       # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="chats")

# ==========================================
# University & Program Models
# ==========================================

class University(Base):
    __tablename__ = "universities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    global_ranking = Column(Integer, nullable=True)

    programs = relationship("Program", back_populates="university")

class Program(Base):
    __tablename__ = "programs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    university_id = Column(String, ForeignKey("universities.id"), nullable=False)
    course_name = Column(String, nullable=False)
    degree_level = Column(String, nullable=True)
    tuition_fee = Column(Float, nullable=True)
    ielts_requirement = Column(Float, nullable=True)

    university = relationship("University", back_populates="programs")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    program_id = Column(String, ForeignKey("programs.id"), nullable=False)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    
    user = relationship("User", back_populates="applications")

class Scholarship(Base):
    __tablename__ = "scholarships"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    criteria = Column(Text, nullable=True)