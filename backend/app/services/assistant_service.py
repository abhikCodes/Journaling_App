from app.config import settings
from app.models import User
from app.services.journal_service import get_monthly_summary, get_important_events, get_friend_personality
from app.utils.ai import ai_manager
import json

# Define the assistant instructions
ASSISTANT_INSTRUCTIONS = """You are a psychology expert assistant designed to help users with their journaling and personal insights. You have access to a library of psychology texts via file search and can retrieve information to support your advice. You can also access summaries and insights from the user's journal entries through function calls. Be empathetic, supportive, and provide informed responses. Include a disclaimer when appropriate: 'I am not a substitute for professional help; please consult a licensed therapist for serious concerns.'"""

# Store the assistant ID after creation
assistant_id = None

async def init_assistant():
    """Initialize the assistant on startup"""
    global assistant_id
    
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


async def handle_assistant_message(user: User, message: str):
    """Handle user messages to the assistant"""
    if not user.thread_id:
        # No existing thread for this user, create a new one
        thread = await ai_manager.get_response(
            user_message=message,
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
        
        return thread["response"]
    else:
        # Use existing thread for this user
        thread_id = user.thread_id
        
        # Define tool callbacks with proper async handling
        async def monthly_summary_callback():
            return await get_monthly_summary(user)
            
        async def important_events_callback():
            return await get_important_events(user)
            
        async def friend_personality_callback(f_name):
            return await get_friend_personality(user, f_name)
        
        # Get response using the AI Manager
        result = await ai_manager.get_response(
            user_message=message,
            thread_id=thread_id,
            assistant_id=assistant_id,
            tool_callbacks={
                "get_monthly_summary": monthly_summary_callback,
                "get_important_events": important_events_callback,
                "get_friend_personality": friend_personality_callback
            }
        )
        
        return result["response"]
