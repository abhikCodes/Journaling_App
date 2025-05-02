from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.models import User, JournalEntry
from app.routes.auth import get_current_user
from app.utils.vector_db_utils import search_similar_entries
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

@router.get("/people-summary")
async def get_people_summary(user: User = Depends(get_current_user)):
    """
    Generate a summary about people mentioned in journal entries
    """
    try:
        # Get all entries
        entries = await JournalEntry.filter(user=user).order_by("-date")
        
        if not entries:
            return {"summary": "No journal entries found to analyze."}
        
        # Concatenate entries for analysis
        entries_text = "\n\n".join([
            f"Date: {entry.date}\nContent: {entry.content}" 
            for entry in entries
        ])
        
        # Generate people summary using OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Analyze these journal entries and create a summary about the people mentioned. Focus on relationships, interactions, and patterns you notice."},
                {"role": "user", "content": entries_text}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        people_summary = response.choices[0].message.content.strip()
        return {"summary": people_summary}
    
    except Exception as e:
        logger.error(f"Failed to generate people summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate people summary")

@router.post("/chat")
async def journal_chat(query: str, user: User = Depends(get_current_user)):
    """
    Chat with your journal entries - ask questions and get answers based on your entries
    """
    try:
        # Get relevant entries using vector search
        relevant_entries = await search_similar_entries(
            user_id=user.id,
            query=query,
            limit=5
        )
        
        if not relevant_entries:
            return {"answer": "I don't have enough information in your journal entries to answer that question."}
        
        # Format entries for context
        context = "\n\n".join([
            f"Date: {entry['date']}\nContent: {entry['content']}" 
            for entry in relevant_entries
        ])
        
        # Generate response using OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that answers questions based on the user's journal entries. Use only the information provided in the entries to answer."},
                {"role": "user", "content": f"Here are some of my journal entries:\n\n{context}\n\nMy question is: {query}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content.strip()
        return {"answer": answer}
    
    except Exception as e:
        logger.error(f"Failed to process chat query: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chat query") 