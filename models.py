from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship
from .db import Base

# -------------------------------------------------
# TEACHER MODEL
# -------------------------------------------------
class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    sessions = relationship("Session", back_populates="teacher", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Teacher(id={self.id}, email='{self.email}')>"


# -------------------------------------------------
# SESSION MODEL
# -------------------------------------------------
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=False, nullable=False)  # added for session control
    word_limit = Column(Integer, default=3)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"))

    # relationships
    teacher = relationship("Teacher", back_populates="sessions")
    responses = relationship("Response", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(code='{self.code}', active={self.is_active})>"


# -------------------------------------------------
# RESPONSE MODEL
# -------------------------------------------------
class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(100))  # student's full name
    word = Column(String(50), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    session = relationship("Session", back_populates="responses")

    def __repr__(self):
        return f"<Response(student='{self.student_name}', word='{self.word}')>"
