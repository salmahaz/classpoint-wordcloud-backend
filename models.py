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
from db import Base

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
    classes = relationship("Classroom", back_populates="teacher", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Teacher(id={self.id}, email='{self.email}')>"


# -------------------------------------------------
# CLASS MODEL (NEW)
# -------------------------------------------------
class Classroom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"))

    teacher = relationship("Teacher", back_populates="classes")
    students = relationship("Student", back_populates="classroom", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="classroom", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Class(id={self.id}, name='{self.name}')>"


# -------------------------------------------------
# STUDENT MODEL (NEW)
# -------------------------------------------------
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"))

    classroom = relationship("Classroom", back_populates="students")
    responses = relationship("Response", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student(id={self.id}, name='{self.full_name}')>"


# -------------------------------------------------
# SESSION MODEL
# -------------------------------------------------
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    word_limit = Column(Integer, default=3)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))

    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"))

    classroom = relationship("Classroom", back_populates="sessions")
    responses = relationship("Response", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(code='{self.code}', active={self.is_active})>"


# -------------------------------------------------
# RESPONSE MODEL
# -------------------------------------------------
class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(50), nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"))
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))

    student = relationship("Student", back_populates="responses")
    session = relationship("Session", back_populates="responses")

    def __repr__(self):
        return f"<Response(student_id={self.student_id}, word='{self.word}')>"
