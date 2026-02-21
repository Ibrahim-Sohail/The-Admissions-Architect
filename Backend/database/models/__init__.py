"""
Database models for the Admission Architect application.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database.connection import Base

# Association table for many-to-many relationship
user_saved_programs = Table(
    'user_saved_programs',
    Base.metadata,
    Column('user_id', String, ForeignKey('user.id'), primary_key=True),
    Column('program_id', Integer, ForeignKey('program.id'), primary_key=True),
)


class ApplicationStatus(str, enum.Enum):
    """Application status enum."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WAITLISTED = "waitlisted"


class TestType(str, enum.Enum):
    """Test type enum."""
    GRE = "gre"
    IELTS = "ielts"
    TOEFL = "toefl"
    SAT = "sat"


class User(Base):
    """User model."""
    __tablename__ = "user"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=False)          # ← ADD THIS
    verification_token = Column(String, nullable=True) 
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)  # False until email verified
    verification_token = Column(String, nullable=True)
    # Relationships
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    chat_messages = relationship("ChatMessage", back_populates="user")
    test_sessions = relationship("TestSession", back_populates="user")
    applications = relationship("Application", back_populates="user")
    saved_programs = relationship("Program", secondary=user_saved_programs)


class StudentProfile(Base):
    """Student profile model."""
    __tablename__ = "student_profile"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user.id'), unique=True)
    
    # Academic info
    current_education = Column(String)  # Current degree level
    gpa = Column(Float)
    
    # Financial info
    budget_min = Column(Float)
    budget_max = Column(Float)
    
    # Career info
    career_goal = Column(Text)
    
    # Updated timestamp
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="profile")


class TestSession(Base):
    """Test prep session model."""
    __tablename__ = "test_session"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user.id'))
    test_type = Column(SQLEnum(TestType))
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="test_sessions")


class ChatMessage(Base):
    """Chat message model."""
    __tablename__ = "chat_message"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user.id'))
    content = Column(Text)
    sender = Column(String)  # 'user' or 'assistant'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="chat_messages")


class University(Base):
    """University model."""
    __tablename__ = "university"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    country = Column(String)
    city = Column(String)
    website = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    programs = relationship("Program", back_populates="university")


class Program(Base):
    """Academic program model."""
    __tablename__ = "program"
    
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('university.id'))
    name = Column(String)
    degree_level = Column(String)  # e.g., 'Masters', 'Undergraduate'
    field = Column(String)  # e.g., 'Computer Science'
    tuition_fee = Column(Float, nullable=True)
    duration_months = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    university = relationship("University", back_populates="programs")
    applications = relationship("Application", back_populates="program")


class Application(Base):
    """University application model."""
    __tablename__ = "application"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user.id'))
    program_id = Column(Integer, ForeignKey('program.id'))
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="applications")
    program = relationship("Program", back_populates="applications")


class Scholarship(Base):
    """Scholarship model."""
    __tablename__ = "scholarship"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    university_id = Column(Integer, ForeignKey('university.id'), nullable=True)
    amount = Column(Float)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


__all__ = [
    "User",
    "StudentProfile",
    "TestSession",
    "ChatMessage",
    "University",
    "Program",
    "Application",
    "Scholarship",
    "user_saved_programs",
    "ApplicationStatus",
    "TestType",
]
