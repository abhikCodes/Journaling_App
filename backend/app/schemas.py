from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime

class JournalEntryCreate(BaseModel):
    date: date
    content: str
    title: Optional[str] = None
    tags: Optional[List[str]] = []
    # image will be handled separately through FormData

    @validator('date')
    def date_not_in_future(cls, v):
        if v > date.today():
            raise ValueError("Journal entry date cannot be in the future")
        return v
    
    @validator('content')
    def content_min_length(cls, v):
        if not v or len(v.split()) < 20:
            word_count = len(v.split()) if v else 0
            raise ValueError(f"Journal entries must contain at least 20 words. Current word count: {word_count}")
        return v
    
    @validator('title')
    def title_max_length(cls, v):
        if v and len(v) > 100:
            raise ValueError("Title cannot exceed 100 characters")
        return v

class JournalEntryUpdate(BaseModel):
    date: Optional[date]
    content: Optional[str]
    title: Optional[str]
    tags: Optional[List[str]]
    # image will be handled separately through FormData
    
    @validator('date')
    def date_not_in_future(cls, v):
        if v and v > date.today():
            raise ValueError("Journal entry date cannot be in the future")
        return v
    
    @validator('content')
    def content_min_length(cls, v):
        if v is not None and (not v or len(v.split()) < 20):
            word_count = len(v.split()) if v else 0
            raise ValueError(f"Journal entries must contain at least 20 words. Current word count: {word_count}")
        return v
    
    @validator('title')
    def title_max_length(cls, v):
        if v and len(v) > 100:
            raise ValueError("Title cannot exceed 100 characters")
        return v

class JournalEntryResponse(BaseModel):
    id: int
    date: date
    content: str
    title: Optional[str] = None
    tags: List[str]
    sentiment_score: Optional[float] = None
    emotion_tags: Optional[List[str]] = []
    image_url: Optional[str] = None

class AssistantRequest(BaseModel):
    message: str

class AssistantMessage(BaseModel):
    message: str

class DebugResponse(BaseModel):
    message: str
    context: str
    enhanced_message: str

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

class TitleGenerationRequest(BaseModel):
    content: str

class CoverImageRequest(BaseModel):
    content: str
    title: Optional[str] = None
