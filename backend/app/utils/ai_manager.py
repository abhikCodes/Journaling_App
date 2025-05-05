"""
OpenAI API management utilities for assistants.

This module provides helper functions for working with the OpenAI Assistants API,
including creating and managing assistants, threads, and messages.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from openai import OpenAI
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Constants
POLLING_INTERVAL = 1.0  # Seconds between polling for run status
MAX_POLLING_ATTEMPTS = 60  # Maximum number of polling attempts (60 = ~1 minute timeout)

def create_assistant(
    name: str,
    instructions: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    model: str = "gpt-4o"
) -> Any:
    """
    Create a new OpenAI assistant.
    
    Args:
        name: Name of the assistant
        instructions: System instructions for the assistant
        tools: List of tools to enable for the assistant
        model: OpenAI model to use
        
    Returns:
        The created assistant object
    """
    try:
        logger.info(f"Creating new assistant: {name}")
        
        # Create the assistant
        assistant = client.beta.assistants.create(
            name=name,
            instructions=instructions,
            tools=tools or [],
            model=model
        )
        
        logger.info(f"Successfully created assistant with ID: {assistant.id}")
        return assistant
    except Exception as e:
        logger.error(f"Error creating assistant: {e}")
        raise

def create_thread() -> Any:
    """
    Create a new thread for conversation.
    
    Returns:
        The created thread object
    """
    try:
        logger.info("Creating new thread")
        thread = client.beta.threads.create()
        logger.info(f"Created thread with ID: {thread.id}")
        return thread
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        raise

def add_message_to_thread(thread_id: str, role: str, content: str) -> Any:
    """
    Add a message to an existing thread.
    
    Args:
        thread_id: ID of the thread
        role: Role of the message sender ("user" or "assistant")
        content: Message content
        
    Returns:
        The created message object
    """
    try:
        logger.info(f"Adding {role} message to thread {thread_id}")
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )
        logger.info(f"Added message with ID: {message.id}")
        return message
    except Exception as e:
        logger.error(f"Error adding message to thread: {e}")
        raise

def run_assistant(thread_id: str, assistant_id: str) -> Any:
    """
    Run the assistant on a thread.
    
    Args:
        thread_id: ID of the thread
        assistant_id: ID of the assistant
        
    Returns:
        The created run object
    """
    try:
        logger.info(f"Starting assistant run in thread {thread_id}")
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        logger.info(f"Started run with ID: {run.id}")
        return run
    except Exception as e:
        logger.error(f"Error running assistant: {e}")
        raise

def get_run_status(thread_id: str, run_id: str) -> Any:
    """
    Poll for the status of an assistant run until completion.
    
    Args:
        thread_id: ID of the thread
        run_id: ID of the run
        
    Returns:
        The final run object
    """
    try:
        logger.info(f"Polling for run status (run_id: {run_id})")
        
        attempts = 0
        while attempts < MAX_POLLING_ATTEMPTS:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            if run.status in ["completed", "failed", "cancelled", "expired"]:
                logger.info(f"Run completed with status: {run.status}")
                return run
            
            logger.info(f"Run status: {run.status}, waiting...")
            time.sleep(POLLING_INTERVAL)
            attempts += 1
        
        logger.warning(f"Run polling timed out after {MAX_POLLING_ATTEMPTS} attempts")
        return run
    except Exception as e:
        logger.error(f"Error getting run status: {e}")
        raise

def get_thread_messages(thread_id: str, limit: int = 10) -> List[Any]:
    """
    Get messages from a thread.
    
    Args:
        thread_id: ID of the thread
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message objects
    """
    try:
        logger.info(f"Getting messages from thread {thread_id}")
        messages = client.beta.threads.messages.list(
            thread_id=thread_id,
            limit=limit
        )
        return messages.data
    except Exception as e:
        logger.error(f"Error getting thread messages: {e}")
        raise

def get_run_steps(thread_id: str, run_id: str) -> List[Any]:
    """
    Get the steps performed during an assistant run.
    
    Args:
        thread_id: ID of the thread
        run_id: ID of the run
        
    Returns:
        List of run step objects
    """
    try:
        logger.info(f"Getting steps for run {run_id}")
        steps = client.beta.threads.runs.steps.list(
            thread_id=thread_id,
            run_id=run_id
        )
        return steps.data
    except Exception as e:
        logger.error(f"Error getting run steps: {e}")
        raise 