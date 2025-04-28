from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)  # Google user ID
    email = Column(String, unique=True, index=True)
    name = Column(String)
    entries = relationship("JournalEntry", back_populates="user")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    text = Column(String)
    image_url = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    user = relationship("User", back_populates="entries")