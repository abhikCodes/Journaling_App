from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.schemas import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse
from app.models import JournalEntry, User, PeriodicSummary
from app.routes.auth import get_current_user
from app.utils.vector_db_utils import store_journal_entry, delete_journal_entry, search_similar_entries
from app.utils.sentiment_utils import analyze_sentiment, generate_periodic_summary
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/entries", response_model=JournalEntryResponse)
async def create_entry(entry: JournalEntryCreate, user: User = Depends(get_current_user)):
    # Analyze sentiment
    sentiment_score, emotion_tags = await analyze_sentiment(entry.content)
    
    # Create the entry
    new_entry = await JournalEntry.create(
        user=user,
        date=entry.date,
        content=entry.content,
        tags=entry.tags,
        sentiment_score=sentiment_score,
        emotion_tags=emotion_tags
    )
    
    # Store in vector database
    try:
        await store_journal_entry(
            entry_id=new_entry.id,
            user_id=user.id,
            content=entry.content,
            date=str(entry.date),
            tags=entry.tags
        )
    except Exception as e:
        logger.error(f"Failed to store entry in vector DB: {str(e)}")
    
    # Update user's entry count
    user.entry_count += 1
    await user.save()
    
    # Check if we need to generate a periodic summary (every 15 entries)
    if user.entry_count >= user.last_summary_count + 15:
        try:
            # Get recent entries
            recent_entries = await JournalEntry.filter(
                user=user
            ).order_by("-date").limit(15)
            
            # Format entries for summary
            entries_text = "\n\n".join([
                f"Date: {entry.date}\nContent: {entry.content}" 
                for entry in recent_entries
            ])
            
            # Generate summary
            summary_content = await generate_periodic_summary(entries_text)
            
            # Get date range
            oldest_entry = min(recent_entries, key=lambda x: x.date)
            newest_entry = max(recent_entries, key=lambda x: x.date)
            
            # Create summary record
            await PeriodicSummary.create(
                user=user,
                start_date=oldest_entry.date,
                end_date=newest_entry.date,
                content=summary_content,
                entry_count=15
            )
            
            # Update last summary count
            user.last_summary_count = user.entry_count
            await user.save()
            
        except Exception as e:
            logger.error(f"Failed to generate periodic summary: {str(e)}")
    
    return JournalEntryResponse(
        id=new_entry.id,
        date=new_entry.date,
        content=new_entry.content,
        tags=new_entry.tags,
        sentiment_score=sentiment_score,
        emotion_tags=emotion_tags
    )

@router.get("/entries", response_model=List[JournalEntryResponse])
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
    return [
      JournalEntryResponse(
        id=e.id, date=e.date, content=e.content, tags=e.tags
      )
      for e in entries
    ]

@router.get("/entries/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(entry_id: int, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return JournalEntryResponse(
        id=entry.id,
        date=entry.date,
        content=entry.content,
        tags=entry.tags
    )

@router.put("/entries/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(entry_id: int, entry_data: JournalEntryUpdate, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    update_data = entry_data.dict(exclude_unset=True)
    
    # If content is updated, re-analyze sentiment
    if "content" in update_data:
        sentiment_score, emotion_tags = await analyze_sentiment(update_data["content"])
        update_data["sentiment_score"] = sentiment_score
        update_data["emotion_tags"] = emotion_tags
        
    await entry.update_from_dict(update_data)
    await entry.save()
    
    # Update in vector database if content was changed
    if "content" in update_data or "tags" in update_data:
        try:
            await store_journal_entry(
                entry_id=entry.id,
                user_id=user.id,
                content=entry.content,
                date=str(entry.date),
                tags=entry.tags
            )
        except Exception as e:
            logger.error(f"Failed to update entry in vector DB: {str(e)}")
    
    return JournalEntryResponse(
        id=entry.id,
        date=entry.date,
        content=entry.content,
        tags=entry.tags,
        sentiment_score=entry.sentiment_score,
        emotion_tags=entry.emotion_tags
    )

@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: int, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Delete from vector database
    try:
        await delete_journal_entry(entry_id=entry.id)
    except Exception as e:
        logger.error(f"Failed to delete entry from vector DB: {str(e)}")
    
    await entry.delete()
    return {"message": "Entry deleted"}

@router.get("/search", response_model=List[JournalEntryResponse])
async def semantic_search(query: str, limit: int = 5, user: User = Depends(get_current_user)):
    """
    Search for journal entries semantically similar to the query
    """
    try:
        # Perform semantic search in vector DB
        results = await search_similar_entries(
            user_id=user.id,
            query=query,
            limit=limit
        )
        
        # Format results
        response = []
        for result in results:
            response.append(
                JournalEntryResponse(
                    id=result["id"],
                    date=result["date"],
                    content=result["content"],
                    tags=result["tags"]
                )
            )
        
        return response
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Semantic search failed")
