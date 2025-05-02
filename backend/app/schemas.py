from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime

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
    sentiment_score: Optional[float] = None
    emotion_tags: Optional[List[str]] = []

class AssistantRequest(BaseModel):
    message: str

class AssistantMessage(BaseModel):
    message: str

class PeriodicSummaryResponse(BaseModel):
    id: int
    date_created: datetime
    start_date: date
    end_date: date
    content: str
    entry_count: int

class SentimentAnalysisResponse(BaseModel):
    sentiment_score: float
    emotion_tags: List[str]
    
class SentimentHistoryResponse(BaseModel):
    dates: List[str]
    scores: List[float]
    emotions: Dict[str, int]  # Count of each emotion
