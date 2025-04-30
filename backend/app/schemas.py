from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class JournalEntryCreate(BaseModel):
    date: date
    content: str
    tags: Optional[List[str]] = []

class JournalEntryUpdate(BaseModel):
    date: Optional[date]
    content: Optional[str]
    tags: Optional[List[str]]

class JournalEntryResponse(BaseModel):
    id: int
    date: date
    content: str
    tags: List[str]

class AssistantMessage(BaseModel):
    message: str