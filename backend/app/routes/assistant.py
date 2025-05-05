from fastapi import APIRouter, Depends, Response, status
from app.schemas import AssistantRequest, AssistantMessage, DebugResponse
from app.services.assistant_service import handle_assistant_message, get_relevant_entries, clear_assistant_thread
from app.routes.auth import get_current_user
from app.models import User
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/message", response_model=AssistantMessage)
async def send_message(req: AssistantRequest, user: User = Depends(get_current_user)):
    # Log detailed information about the user
    is_test_user = user.email == "test@example.com" or "test" in user.name.lower()
    logger.info(f"Processing assistant message for user: {user.id} (name: {user.name}, email: {user.email}, is_test_user: {is_test_user})")
    
    # Add query to log
    logger.info(f"Query from user {user.id}: '{req.message}'")
    
    response_data = await handle_assistant_message(user_id=user.id, message_content=req.message)
    
    # Log the response status
    logger.info(f"Response ready for user {user.id}, thread_id: {response_data.get('thread_id')}")
    
    return AssistantMessage(message=response_data["response"])

@router.post("/clear", status_code=200)
async def clear_context(user: User = Depends(get_current_user)):
    """Clear the assistant thread for the current user"""
    logger.info(f"Clearing assistant thread for user {user.id}")
    await clear_assistant_thread(user)
    return {"success": True, "message": "Assistant context cleared"}

@router.post("/debug", response_model=DebugResponse)
async def debug_context(req: AssistantRequest, user: User = Depends(get_current_user)):
    """Debug endpoint to see what context is being sent to the model"""
    context = await get_relevant_entries(query=req.message)
    logger.info(f"Debug request - context: {context}")
    
    # Log the message and context that would be sent to the model
    if context:
        enhanced_message = f"[CONTEXT] {context} [END CONTEXT]\n\nUser message: {req.message}"
    else:
        enhanced_message = req.message
    
    return DebugResponse(
        message=req.message,
        context=context,
        enhanced_message=enhanced_message
    )
