from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.schemas import JournalEntryCreate, JournalEntryUpdate
from app.models import JournalEntry, User
from app.routes.auth import get_current_user
from datetime import date

router = APIRouter()

@router.post("/entries", response_model=dict)
async def create_entry(entry: JournalEntryCreate, user: User = Depends(get_current_user)):
    new_entry = await JournalEntry.create(
        user=user,
        date=entry.date,
        content=entry.content,
        tags=entry.tags
    )
    return {"id": new_entry.id, "date": new_entry.date, "content": new_entry.content, "tags": new_entry.tags}

@router.get("/entries", response_model=List[dict])
async def list_entries(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user: User = Depends(get_current_user)
):
    query = JournalEntry.filter(user=user)
    if search:
        query = query.filter(content__icontains=search)
    if tag:
        query = query.filter(tags__contains=[tag])
    if start_date:
        query = query.filter(date__gte=start_date)
    if end_date:
        query = query.filter(date__lte=end_date)
    entries = await query.offset(skip).limit(limit)
    return [{"id": e.id, "date": e.date, "content": e.content, "tags": e.tags} for e in entries]

@router.get("/entries/{entry_id}", response_model=dict)
async def get_entry(entry_id: int, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"id": entry.id, "date": entry.date, "content": entry.content, "tags": entry.tags}

@router.put("/entries/{entry_id}", response_model=dict)
async def update_entry(entry_id: int, entry_data: JournalEntryUpdate, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    update_data = entry_data.dict(exclude_unset=True)
    await entry.update_from_dict(update_data)
    await entry.save()
    return {"id": entry.id, "date": entry.date, "content": entry.content, "tags": entry.tags}

@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: int, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await entry.delete()
    return {"message": "Entry deleted"}