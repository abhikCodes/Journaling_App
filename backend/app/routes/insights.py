from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.models import User, JournalEntry
from app.routes.auth import get_current_user
import logging
from openai import AsyncOpenAI
from app.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

router = APIRouter()

@router.get("/summary")
async def get_journal_summary(user: User = Depends(get_current_user)):
    """
    Generate a summary of recent journal entries
    """
    try:
        # Get recent entries
        entries = await JournalEntry.filter(user=user).order_by("-date").limit(10)
        
        if not entries:
            return {"summary": "No journal entries found to summarize."}
        
        # Concatenate entries for analysis
        entries_text = "\n\n".join([
            f"Date: {entry.date}\nContent: {entry.content}" 
            for entry in entries
        ])
        
        # Generate summary using OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes journal entries. Create a short, insightful summary of the key themes, emotions, and events from these journal entries."},
                {"role": "user", "content": entries_text}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        return {"summary": summary}
    
    except Exception as e:
        logger.error(f"Failed to generate summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate summary") 