from app.config import settings
from app.models import User
from app.services.journal_service import get_monthly_summary, get_important_events, get_friend_personality
from app.utils.ai import ai_manager
from app.utils.vector_db_utils import search_similar_entries
from app.config.prompts import ASSISTANT_PROMPTS
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get assistant instructions from centralized prompts
ASSISTANT_INSTRUCTIONS = ASSISTANT_PROMPTS["JOURNAL_ASSISTANT"]

# Store the assistant ID after creation
assistant_id = None

async def init_assistant():
    """Initialize the assistant on-demand (only when needed)"""
    global assistant_id
    
    # Only initialize if not already initialized
    if assistant_id is not None:
        logger.info(f"Assistant already initialized with ID: {assistant_id}")
        return assistant_id
        
    logger.info("Initializing assistant on-demand")
    
    # Define the tools for the assistant
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_monthly_summary",
                "description": "Get a summary of the user's journal entries for the last 30 days.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_important_events",
                "description": "Identify significant events from the user's journal entries for the last 30 days.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_friend_personality",
                "description": "Summarize a friend's personality from the user's journal entries for the last 30 days.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "f_name": {
                            "type": "string",
                            "description": "The first name of the friend to analyze."
                        }
                    },
                    "required": ["f_name"]
                }
            }
        }
    ]
    
    # Create the assistant using the AI Manager
    assistant = await ai_manager.create_assistant(
        name="PsychologyExpert",
        instructions=ASSISTANT_INSTRUCTIONS,
        tools=tools
    )
    
    # Store the assistant ID
    assistant_id = assistant["id"]
    ai_manager.set_active_assistant_id(assistant_id)
    logger.info(f"Assistant initialized with ID: {assistant_id}")
    return assistant_id

async def get_relevant_entries(user: User, message: str):
    """Retrieve relevant journal entries based on the user's message"""
    try:
        # Search for relevant entries in vector DB
        entries = await search_similar_entries(user.id, message, limit=3)
        
        if not entries:
            logger.info(f"No relevant entries found for user {user.id}")
            return ""
        
        # Format the entries as a context block
        context = "Here are some relevant journal entries that might help you provide a better response note they might or might not be usefull go trhough them to find any thing important that you can use to help the user :\n\n"
        
        for i, entry in enumerate(entries):
            context += f"Entry {i+1} (Date: {entry['date']}):\n{entry['content']}\n\n"
            
        logger.info(f"Found {len(entries)} relevant entries for user {user.id}")
        return context
    except Exception as e:
        logger.error(f"Error retrieving relevant entries: {str(e)}")
        return ""

async def handle_assistant_message(user: User, message: str):
    """Handle user messages to the assistant"""
    global assistant_id
    
    # Make sure assistant is initialized (lazy initialization)
    if assistant_id is None:
        assistant_id = await init_assistant()
    
    # Fetch relevant context from the user's journal entries
    relevant_context = await get_relevant_entries(user, message)
    
    # Log the context for debugging
    logger.info(f"Context for message: {relevant_context}")
    
    # If we have relevant context, prepend it to the user's message
    enhanced_message = message
    if relevant_context:
        enhanced_message = f"[CONTEXT] {relevant_context} [END CONTEXT]\n\nUser message: {message}"
    
    if not user.thread_id:
        # No existing thread for this user, create a new one
        logger.info(f"Creating new thread for user {user.id}")
        thread = await ai_manager.get_response(
            user_message=enhanced_message,
            assistant_id=assistant_id,
            tool_callbacks={
                "get_monthly_summary": lambda: get_monthly_summary(user),
                "get_important_events": lambda: get_important_events(user),
                "get_friend_personality": lambda f_name: get_friend_personality(user, f_name)
            }
        )
        
        # Save the thread ID to the user
        user.thread_id = thread["thread_id"]
        await user.save()
        logger.info(f"Created new thread with ID {thread['thread_id']} for user {user.id}")
        
        return thread["response"]
    else:
        # Use existing thread for this user
        thread_id = user.thread_id
        logger.info(f"Using existing thread {thread_id} for user {user.id}")
        
        # Define tool callbacks with proper async handling
        async def monthly_summary_callback():
            return await get_monthly_summary(user)
            
        async def important_events_callback():
            return await get_important_events(user)
            
        async def friend_personality_callback(f_name):
            return await get_friend_personality(user, f_name)
        
        try:
            # Get response using the AI Manager
            result = await ai_manager.get_response(
                user_message=enhanced_message,
                thread_id=thread_id,
                assistant_id=assistant_id,
                tool_callbacks={
                    "get_monthly_summary": monthly_summary_callback,
                    "get_important_events": important_events_callback,
                    "get_friend_personality": friend_personality_callback
                }
            )
            
            logger.info(f"Successfully received response using thread {thread_id}")
            return result["response"]
        except Exception as e:
            logger.error(f"Error getting response with existing thread: {str(e)}")
            logger.info(f"Creating new thread for user {user.id} due to error with existing thread")
            
            # If there was an error with the existing thread, create a new one
            thread = await ai_manager.get_response(
                user_message=enhanced_message,
                assistant_id=assistant_id,
                tool_callbacks={
                    "get_monthly_summary": monthly_summary_callback,
                    "get_important_events": important_events_callback,
                    "get_friend_personality": friend_personality_callback
                }
            )
            
            # Save the new thread ID to the user
            user.thread_id = thread["thread_id"]
            await user.save()
            logger.info(f"Created new thread with ID {thread['thread_id']} for user {user.id}")
            
            return thread["response"]

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
