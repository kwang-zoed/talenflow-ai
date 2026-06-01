from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean

Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="candidate")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # resumes = relationship("ResumeDB", back_populates="user", cascade="all, delete-orphan")
    # applications = relationship("ApplicationDB", back_populates="user")
    # sessions = relationship("ChatSessionDB", back_populates="user", cascade="all, delete-orphan")
    # deliveries = relationship("TaskDeliveryDB", back_populates="user")