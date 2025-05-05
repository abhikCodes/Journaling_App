from app.config import settings
from app.models import User
from app.services.journal_service import get_monthly_summary, get_important_events, get_friend_personality
from app.utils.ai import ai_manager
from app.utils.vector_db_utils import search_similar_entries
from app.utils.advanced_retrieval import get_relevant_entries_advanced
from app.config.prompts import ASSISTANT_PROMPTS
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from openai import OpenAI
from app.utils.ai_manager import create_assistant, create_thread, add_message_to_thread, run_assistant, get_run_status, get_thread_messages, get_run_steps

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Get assistant instructions from centralized prompts
ASSISTANT_INSTRUCTIONS = ASSISTANT_PROMPTS["JOURNAL_ASSISTANT"]

# Store the assistant ID after creation
assistant_id = None

# Helper function to format entries for context
def format_entries_for_context(entries: List[Dict[str, Any]]) -> str:
    """Format journal entries for inclusion in the context"""
    if not entries:
        return ""
        
    context = ""
    for entry in entries:
        date_str = entry["date"].strftime("%Y-%m-%d") if entry.get("date") else "Unknown date"
        title = entry.get("title", "No title")
        content = entry.get("content", "")
        context += f"[{date_str}] {title}\n{content}\n\n"
    
    return context.strip()

async def process_message_with_ai(message_content: str, context: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a message with OpenAI using the assistant API
    
    Args:
        message_content: User's message
        context: Context from journal entries
        thread_id: Optional thread ID for continuing a conversation
        
    Returns:
        Dictionary with response and thread information
    """
    try:
        # Initialize or get assistant
        global assistant_id
        if not assistant_id:
            assistant_id = init_assistant()
            
        # Create a new thread if none is provided
        if not thread_id:
            logger.info("[AssistantService] Creating new thread")
            thread = create_thread()
            thread_id = thread.id
        
        logger.info(f"[AssistantService] Processing message in thread {thread_id}")
        
        # Prepare user message with context
        if context:
            enhanced_message = f"{message_content}\n\n[CONTEXT]\n{context}\n[/CONTEXT]"
            logger.info(f"[AssistantService] Added context to message ({len(context)} chars)")
        else:
            enhanced_message = message_content
            logger.info("[AssistantService] No context available for this message")
        
        # Add user message to the thread
        add_message_to_thread(thread_id=thread_id, role="user", content=enhanced_message)
        
        # Run the assistant
        run = run_assistant(thread_id=thread_id, assistant_id=assistant_id)
        run_id = run.id
        
        # Wait for the run to complete
        final_run = get_run_status(thread_id=thread_id, run_id=run_id)
        
        if final_run.status != "completed":
            logger.error(f"[AssistantService] Run failed with status: {final_run.status}")
            if final_run.status == "failed":
                # If the thread is causing issues, create a new one
                logger.info("[AssistantService] Creating new thread due to run failure")
                thread = create_thread()
                thread_id = thread.id
                
                # Add simple message to the new thread
                add_message_to_thread(thread_id=thread_id, role="user", content=message_content)
                
                # Run the assistant again without context
                run = run_assistant(thread_id=thread_id, assistant_id=assistant_id)
                run_id = run.id
                
                # Wait for the run to complete
                final_run = get_run_status(thread_id=thread_id, run_id=run_id)
                
                if final_run.status != "completed":
                    return {
                        "response": "I'm having trouble processing your request. Please try again later.",
                        "thread_id": thread_id
                    }
            else:
                return {
                    "response": "I'm having trouble processing your request. Please try again later.",
                    "thread_id": thread_id
                }
        
        # Get messages from the thread
        messages = get_thread_messages(thread_id=thread_id)
        
        # Get the latest assistant message
        latest_assistant_message = next((msg for msg in messages if msg.role == "assistant"), None)
        
        if not latest_assistant_message:
            return {
                "response": "I couldn't generate a response. Please try again.",
                "thread_id": thread_id
            }
        
        # Extract response content
        response_content = latest_assistant_message.content[0].text.value
        
        # Log success
        logger.info(f"[AssistantService] Successfully generated response ({len(response_content)} chars)")
        
        return {
            "response": response_content,
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"[AssistantService] Error processing message with AI: {str(e)}")
        logger.exception(e)
        return {
            "response": "I encountered an error processing your request. Please try again.",
            "thread_id": thread_id
        }

def init_assistant() -> str:
    """
    Initialize or retrieve the assistant ID.
    
    Returns:
        The assistant ID
    """
    global assistant_id
    
    if assistant_id:
        logger.info(f"Using existing assistant with ID: {assistant_id}")
        return assistant_id
    
    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_monthly_summary",
                "description": "Get a summary of journal entries for a specific month",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "The year (e.g., 2023)"
                        },
                        "month": {
                            "type": "integer",
                            "description": "The month (1-12)"
                        }
                    },
                    "required": ["year", "month"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_important_events",
                "description": "Get important events from journal entries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of events to return (default: 5)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_friend_personality",
                "description": "Get personality insights about a friend mentioned in journal entries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the friend to analyze"
                        }
                    },
                    "required": ["name"]
                }
            }
        }
    ]
    
    # Get instructions from config
    instructions = ASSISTANT_PROMPTS.get("JOURNAL_ASSISTANT", "")
    
    # Create the assistant
    new_assistant = create_assistant(
        name="JournalMind Assistant",
        instructions=instructions,
        tools=tools,
        model="gpt-4o"
    )
    
    assistant_id = new_assistant.id
    logger.info(f"Created new assistant with ID: {assistant_id}")
    
    return assistant_id

def get_relevant_entries(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Get relevant journal entries for a query.
    This is a wrapper function that uses the legacy search for compatibility.
    
    Args:
        query: User's query text
        limit: Maximum number of entries to return
        
    Returns:
        Dictionary with entries, context, and metadata
    """
    try:
        # Use the legacy search function for compatibility
        entries = search_similar_entries(query=query, limit=limit)
        
        if not entries:
            return {
                "entries": [],
                "context": "",
                "metadata": {"count": 0}
            }
        
        # Create context from entries
        context = ""
        for entry in entries:
            date_str = entry["date"].strftime("%Y-%m-%d") if entry["date"] else "Unknown date"
            context += f"[{date_str}] {entry['content']}\n\n"
        
        return {
            "entries": entries,
            "context": context,
            "metadata": {"count": len(entries)}
        }
    except Exception as e:
        logger.error(f"Error getting relevant entries: {e}")
        return {"entries": [], "context": "", "metadata": {"error": str(e), "count": 0}}

async def handle_assistant_message(user_id: int, message_content: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle a message from the user to the assistant
    """
    logger.info(f"[AssistantService] Processing message for user_id: {user_id}")
    logger.info(f"[AssistantService] Message content: '{message_content}'")
    
    try:
        # Get relevant journal entries using advanced retrieval
        logger.info(f"[AssistantService] Retrieving relevant entries for user {user_id}")
        relevant_entries = await get_relevant_entries_advanced(user_id=user_id, query=message_content)
        
        # Process the entries
        if relevant_entries:
            logger.info(f"[AssistantService] Found {len(relevant_entries)} relevant entries for query")
            
            # Format entries for context
            context = format_entries_for_context(relevant_entries)
            logger.info(f"[AssistantService] Generated context ({len(context)} chars) from {len(relevant_entries)} entries")
            
            # Log the details of the retrieved entries
            for i, entry in enumerate(relevant_entries[:5]):  # Log first 5 entries
                entry_id = entry.get('id', 'unknown')
                date = entry.get('date', 'unknown date')
                title = entry.get('title', 'no title')
                score = entry.get('similarity', 'no score')
                logger.info(f"[AssistantService] Entry #{i+1}: ID={entry_id}, Date={date}, Title={title}, Score={score}")
        else:
            logger.warning(f"[AssistantService] No relevant entries found for user {user_id} with query: '{message_content}'")
            context = ""
        
        # Use OpenAI to generate a response
        ai_response = await process_message_with_ai(message_content, context, thread_id)
        
        return {
            "response": ai_response["response"],
            "thread_id": ai_response.get("thread_id"),
            "context_used": bool(context),
            "entries_count": len(relevant_entries) if relevant_entries else 0
        }
        
    except Exception as e:
        logger.error(f"[AssistantService] Error handling assistant message: {str(e)}")
        logger.exception(e)
        return {
            "response": "I'm sorry, I encountered an error while processing your message. Please try again later.",
            "thread_id": thread_id,
            "context_used": False,
            "entries_count": 0
        }

async def clear_assistant_thread(user: User):
    """Clear the assistant thread for a user to start a fresh conversation"""
    global assistant_id
    
    # Do nothing if assistant was never initialized
    if assistant_id is None:
        logger.info(f"No assistant has been initialized yet")
        return True
        
    if user.thread_id:
        logger.info(f"Clearing thread {user.thread_id} for user {user.id}")
        user.thread_id = None
        await user.save()
        logger.info(f"Thread cleared for user {user.id}")
    else:
        logger.info(f"No thread to clear for user {user.id}")
    
    return True
