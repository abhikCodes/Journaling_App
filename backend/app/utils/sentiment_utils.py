from app.utils.ai.manager import ai_manager
from app.config.prompts import ASSISTANT_PROMPTS
import logging
import json
from typing import Dict, List, Tuple, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

async def analyze_sentiment(text: str) -> Tuple[float, List[str]]:
    """
    Analyze the sentiment of text using the AI manager.
    Returns a tuple of (sentiment_score, emotion_tags).
    Sentiment score is from -1.0 (very negative) to 1.0 (very positive).
    """
    try:
        # Get instructions from centralized prompts
        instructions = ASSISTANT_PROMPTS["SENTIMENT_ANALYZER"]
        
        # Create a temporary assistant
        assistant = await ai_manager.create_assistant(
            name="Sentiment Analyzer",
            instructions=instructions
        )
        
        # Get the response - ai_manager will create a thread internally
        response_data = await ai_manager.get_response(
            user_message=text,
            assistant_id=assistant["id"]
        )
        
        result = response_data["response"].strip()
        
        # Try to parse the JSON from the response
        try:
            # Find the JSON in the response if there's any extra text
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                data = json.loads(json_str)
            else:
                data = json.loads(result)
                
            # Validate and return the sentiment score and emotion tags
            sentiment_score = float(data.get("sentiment_score", 0))
            # Clamp sentiment score to [-1.0, 1.0]
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
            
            emotion_tags = data.get("emotion_tags", [])
            # Ensure emotion_tags is a list of strings
            if not isinstance(emotion_tags, list):
                emotion_tags = []
            
            return sentiment_score, emotion_tags
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {result}")
            return 0.0, []
        
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        # Return neutral sentiment if analysis fails
        return 0.0, []

async def generate_periodic_summary(entries_text: str) -> str:
    """
    Generate a summary of multiple journal entries.
    """
    try:
        # Get instructions from centralized prompts
        instructions = ASSISTANT_PROMPTS["JOURNAL_SUMMARIZER"]
        
        # Create a temporary assistant
        assistant = await ai_manager.create_assistant(
            name="Journal Summarizer",
            instructions=instructions
        )
        
        # Get the response - ai_manager will create a thread internally
        response_data = await ai_manager.get_response(
            user_message=entries_text,
            assistant_id=assistant["id"]
        )
        
        return response_data["response"].strip()
        
    except Exception as e:
        logger.error(f"Periodic summary generation error: {str(e)}")
        return "Unable to generate summary at this time." 