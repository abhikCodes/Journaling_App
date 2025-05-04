"""
AI Interaction Logger

This module provides utilities for logging AI interactions to a central log file.
Records both prompts sent to AI and responses received back for debugging and analysis.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Configure a special logger for AI interactions
ai_logger = logging.getLogger("ai_interactions")
ai_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Set up a dedicated file handler for AI interactions
file_handler = logging.FileHandler("logs/ai_interactions.log")
file_handler.setLevel(logging.INFO)

# Create a formatter that includes timestamp
formatter = logging.Formatter('%(asctime)s | %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
ai_logger.addHandler(file_handler)

def log_ai_interaction(
    provider: str,
    prompt_type: str,
    prompt: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an AI interaction to the dedicated log file
    
    Args:
        provider: Name of the AI provider (e.g., "OpenAI", "Ollama")
        prompt_type: Type of prompt (e.g., "sentiment_analysis", "title_generation")
        prompt: The prompt sent to the AI
        response: The response received from the AI
        metadata: Optional metadata about the interaction (e.g., model, user_id)
    """
    # Create a structured log record
    log_record = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "prompt_type": prompt_type,
        "prompt": prompt,
        "response": response[:500] + "..." if len(response) > 500 else response,
        "metadata": metadata or {}
    }
    
    # Log as formatted JSON for easier parsing
    ai_logger.info(json.dumps(log_record, indent=None))

def log_openai_direct_call(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    prompt_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a direct OpenAI API call (used when not going through AI manager)
    
    Args:
        model: The OpenAI model used (e.g., "gpt-4o-mini")
        system_prompt: The system message content
        user_prompt: The user message content
        response: The response from the model
        prompt_type: Type of prompt (e.g., "monthly_summary", "important_events")
        metadata: Optional metadata about the interaction
    """
    prompt = f"System: {system_prompt}\nUser: {user_prompt}"
    
    log_record = {
        "timestamp": datetime.now().isoformat(),
        "provider": "OpenAI Direct",
        "model": model,
        "prompt_type": prompt_type,
        "prompt": prompt,
        "response": response[:500] + "..." if len(response) > 500 else response,
        "metadata": metadata or {}
    }
    
    # Log as formatted JSON for easier parsing
    ai_logger.info(json.dumps(log_record, indent=None)) 