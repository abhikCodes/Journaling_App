from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas, auth
from ..database import get_db
import os
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=schemas.JournalEntryResponse)
async def create_entry(
    text: str,
    tags: str = None,
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: str = Depends(auth.get_current_user)
):
    user = crud.get_user_by_username(db, current_user)
    image_url = None
    if image:
        image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"
        image_path = os.path.join("images", image_filename)
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
        image_url = f"/images/{image_filename}"
    entry = schemas.JournalEntryCreate(text=text, tags=tags)
    db_entry = crud.create_journal_entry(db, entry, user.id, image_url)
    return db_entry

@router.get("/", response_model=list[schemas.JournalEntryResponse])
def get_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: str = Depends(auth.get_current_user)
):
    user = crud.get_user_by_username(db, current_user)
    entries = crud.get_journal_entries(db, user.id, skip, limit)
    return entries