from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

class JournalEntryCreate(BaseModel):
    text: str
    tags: str | None = None

class JournalEntryResponse(BaseModel):
    id: int
    date: datetime
    text: str
    image_url: str | None
    tags: str | None

class AIQuery(BaseModel):
    query: str