from fastapi import APIRouter, HTTPException, Depends, Body, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.assistant_service import handle_assistant_message, clear_assistant_thread
from app.models import User

router = APIRouter()

class AssistantMessageRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class AssistantMessageResponse(BaseModel):
    response: str
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.post("/message", response_model=AssistantMessageResponse)
async def send_message_to_assistant(
    request: AssistantMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to the AI assistant and get a response.
    
    This endpoint:
    1. Takes the user's message
    2. Retrieves relevant journal entries using the advanced retrieval pipeline
    3. Enhances the prompt with this context
    4. Gets a response from the assistant
    
    Returns:
        The assistant's response and thread information
    """
    try:
        # Process the message using the assistant service
        result = handle_assistant_message(
            user_id=current_user.id,
            message_content=request.message,
            thread_id=request.thread_id
        )
        
        # Update the user's thread_id if it's a new thread
        if result.get("thread_id") and not current_user.thread_id:
            current_user.thread_id = result["thread_id"]
            await current_user.save()
        
        return AssistantMessageResponse(
            response=result["response"],
            thread_id=result["thread_id"],
            metadata=result.get("metadata", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.post("/clear-thread")
async def clear_thread(
    current_user: User = Depends(get_current_user)
):
    """
    Clear the user's assistant thread to start a fresh conversation.
    """
    try:
        await clear_assistant_thread(current_user)
        current_user.thread_id = None
        await current_user.save()
        return {"message": "Thread cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing thread: {str(e)}")

@router.get("/status")
async def get_assistant_status():
    """
    Check if the assistant service is online and ready.
    """
    return {
        "status": "online",
        "features": {
            "advanced_retrieval": True,
            "query_expansion": True,
            "hybrid_search": True,
            "entity_recognition": True
        }
    } 