from openai import AsyncOpenAI
from app.config import settings
import logging
from typing import Dict, List, Tuple, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def analyze_sentiment(text: str) -> Tuple[float, List[str]]:
    """
    Analyze the sentiment of text using OpenAI.
    Returns a tuple of (sentiment_score, emotion_tags).
    Sentiment score is from -1.0 (very negative) to 1.0 (very positive).
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.3,
            messages=[
                {"role": "system", "content": 
                 """Analyze the sentiment of the following journal entry. 
                 Return a JSON object with:
                 1. sentiment_score: A number from -1.0 (extremely negative) to 1.0 (extremely positive)
                 2. emotion_tags: An array of emotion words (max 5) that best describe the entry
                 
                 Example response:
                 {"sentiment_score": 0.7, "emotion_tags": ["happy", "relieved", "hopeful"]}
                 
                 Only return the JSON with no additional text or explanations."""},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        # Parse the JSON response
        import json
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
        
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        # Return neutral sentiment if analysis fails
        return 0.0, []

async def generate_periodic_summary(entries_text: str) -> str:
    """
    Generate a summary of multiple journal entries.
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.7,
            messages=[
                {"role": "system", "content": 
                 """You are an insightful journal companion that creates meaningful summaries.
                 Analyze these journal entries and create a 2-3 paragraph summary that:
                 1. Identifies key themes, events, and emotional patterns
                 2. Notes any significant changes or developments
                 3. Provides gentle, supportive observations about the person's recent experiences
                 
                 Be warm, empathetic and personal in your summary.
                 """},
                {"role": "user", "content": entries_text}
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Periodic summary generation error: {str(e)}")
        return "Unable to generate summary at this time." 