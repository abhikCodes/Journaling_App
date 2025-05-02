from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import date, datetime, timedelta
from app.models import User, JournalEntry, PeriodicSummary
from app.routes.auth import get_current_user
from app.schemas import PeriodicSummaryResponse, SentimentHistoryResponse
import logging
from collections import Counter

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/sentiment/history", response_model=SentimentHistoryResponse)
async def get_sentiment_history(
    days: int = 30,
    user: User = Depends(get_current_user)
):
    """
    Get sentiment history data for charting.
    Returns sentiment scores and emotion counts for the specified number of days.
    """
    try:
        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get entries within the date range
        entries = await JournalEntry.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by("date")
        
        if not entries:
            return SentimentHistoryResponse(
                dates=[],
                scores=[],
                emotions={}
            )
        
        # Extract sentiment data
        dates = [entry.date.isoformat() for entry in entries]
        scores = [entry.sentiment_score if entry.sentiment_score is not None else 0.0 for entry in entries]
        
        # Count emotions
        all_emotions = []
        for entry in entries:
            if entry.emotion_tags:
                all_emotions.extend(entry.emotion_tags)
        
        emotion_counts = dict(Counter(all_emotions))
        
        return SentimentHistoryResponse(
            dates=dates,
            scores=scores,
            emotions=emotion_counts
        )
    
    except Exception as e:
        logger.error(f"Failed to get sentiment history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get sentiment history")

@router.get("/summaries", response_model=List[PeriodicSummaryResponse])
async def get_periodic_summaries(
    limit: int = 5,
    user: User = Depends(get_current_user)
):
    """
    Get the most recent periodic summaries
    """
    try:
        summaries = await PeriodicSummary.filter(
            user=user
        ).order_by("-date_created").limit(limit)
        
        return [
            PeriodicSummaryResponse(
                id=summary.id,
                date_created=summary.date_created,
                start_date=summary.start_date,
                end_date=summary.end_date,
                content=summary.content,
                entry_count=summary.entry_count
            )
            for summary in summaries
        ]
    
    except Exception as e:
        logger.error(f"Failed to get periodic summaries: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get periodic summaries")

@router.get("/summaries/{summary_id}", response_model=PeriodicSummaryResponse)
async def get_periodic_summary(
    summary_id: int,
    user: User = Depends(get_current_user)
):
    """
    Get a specific periodic summary by ID
    """
    try:
        summary = await PeriodicSummary.get_or_none(id=summary_id, user=user)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        return PeriodicSummaryResponse(
            id=summary.id,
            date_created=summary.date_created,
            start_date=summary.start_date,
            end_date=summary.end_date,
            content=summary.content,
            entry_count=summary.entry_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get periodic summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get periodic summary")

@router.get("/summaries/latest")
async def get_latest_summary(
    user: User = Depends(get_current_user)
):
    """
    Get the most recent periodic summary
    """
    try:
        summary = await PeriodicSummary.filter(
            user=user
        ).order_by("-date_created").first()
        
        if not summary:
            return {"has_summary": False}
        
        return {
            "has_summary": True,
            "summary": PeriodicSummaryResponse(
                id=summary.id,
                date_created=summary.date_created,
                start_date=summary.start_date,
                end_date=summary.end_date,
                content=summary.content,
                entry_count=summary.entry_count
            )
        }
    
    except Exception as e:
        logger.error(f"Failed to get latest summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get latest summary") 