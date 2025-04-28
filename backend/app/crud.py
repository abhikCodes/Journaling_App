from sqlalchemy.orm import Session
from . import models, schemas

def get_user_by_google_id(db: Session, google_id: str):
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def create_user(db: Session, google_id: str, email: str, name: str):
    db_user = models.User(google_id=google_id, email=email, name=name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_journal_entry(db: Session, entry: schemas.JournalEntryCreate, user_id: int, image_url: str = None):
    db_entry = models.JournalEntry(**entry.dict(), user_id=user_id, image_url=image_url)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_journal_entries(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).offset(skip).limit(limit).all()