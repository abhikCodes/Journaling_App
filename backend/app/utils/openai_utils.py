import logging
import json
from typing import Optional, Dict, Any, List, Union
from openai import OpenAI
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_image_description(content: str, title: Optional[str] = None, model: str = "gpt-4") -> str:
    """
    Generate an image description for a journal entry.
    
    Args:
        content: Journal entry content
        title: Optional journal entry title
        model: OpenAI model to use
        
    Returns:
        Generated image description
    """
    try:
        if title:
            prompt = f"Create a detailed image description based on this journal entry titled \"{title}\". Focus on the emotional tone, setting, and key themes without including people: {content}"
        else:
            prompt = f"Create a detailed image description based on this journal entry. Focus on the emotional tone, setting, and key themes without including people: {content}"
        
        # Set a fallback description in case API fails
        fallback_description = "A peaceful journal sitting on a wooden desk by a window with soft light streaming in."
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a creative image description generator. Create vivid, detailed descriptions that capture the emotional essence of journal entries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Extract and return the generated description
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        else:
            logger.warning("Empty response from OpenAI API")
            return fallback_description
    except Exception as e:
        logger.error(f"Error generating image description: {e}")
        return "A peaceful journal sitting on a wooden desk by a window with soft light streaming in."

def generate_title(content: str, style: str = "friends", model: str = "gpt-3.5-turbo") -> str:
    """
    Generate a title for a journal entry in a specific style.
    
    Args:
        content: Journal entry content
        style: Style of title (e.g., "friends" for Friends TV show style)
        model: OpenAI model to use
        
    Returns:
        Generated title
    """
    try:
        # Create a prompt based on the style
        if style == "friends":
            prompt = "Generate a creative title for this journal entry in the style of Friends TV show episodes (starting with 'The One Where' or 'The One With'). Return only the title, no other text."
        else:
            prompt = "Generate a creative, concise title (5-7 words) for this journal entry that captures its essence. Return only the title, no other text."
            
        # Set a fallback title
        fallback_title = "My Journal Entry"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a creative title generator."},
                {"role": "user", "content": f"{prompt}\n\nJournal entry: {content}"}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        # Extract and return the generated title
        if response.choices and len(response.choices) > 0:
            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"\'')
            return title
        else:
            logger.warning("Empty response from OpenAI API")
            return fallback_title
    except Exception as e:
        logger.error(f"Error generating title: {e}")
        return fallback_title

def analyze_sentiment(content: str, model: str = "gpt-4") -> Dict[str, Any]:
    """
    Analyze the sentiment of a journal entry.
    
    Args:
        content: Journal entry content
        model: OpenAI model to use
        
    Returns:
        Dictionary with sentiment analysis results
    """
    try:
        # Create a prompt for sentiment analysis
        prompt = """
        Analyze the sentiment of this journal entry. Return a JSON with the following structure:
        {
            "primary_emotion": "happy|sad|angry|anxious|neutral|etc",
            "emotion_intensity": 0-10,
            "overall_sentiment": "positive|negative|neutral|mixed",
            "sentiment_score": -10 to 10 (negative to positive),
            "key_themes": ["theme1", "theme2", ...]
        }
        Only return the JSON, no other text.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a sentiment analysis expert."},
                {"role": "user", "content": f"{prompt}\n\nJournal entry: {content}"}
            ],
            max_tokens=300,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Extract and parse the JSON response
        if response.choices and len(response.choices) > 0:
            result_text = response.choices[0].message.content.strip()
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                logger.error(f"Error parsing JSON response: {result_text}")
                return {
                    "primary_emotion": "neutral",
                    "emotion_intensity": 5,
                    "overall_sentiment": "neutral",
                    "sentiment_score": 0,
                    "key_themes": ["unknown"]
                }
        else:
            logger.warning("Empty response from OpenAI API")
            return {
                "primary_emotion": "neutral",
                "emotion_intensity": 5,
                "overall_sentiment": "neutral",
                "sentiment_score": 0,
                "key_themes": ["unknown"]
            }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {
            "primary_emotion": "neutral",
            "emotion_intensity": 5,
            "overall_sentiment": "neutral",
            "sentiment_score": 0,
            "key_themes": ["unknown"]
        }

def generate_openai_completion(
    prompt: str,
    user_content: str,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Generate text completion using OpenAI API.
    
    Args:
        prompt: System prompt
        user_content: User content/query
        model: OpenAI model to use
        temperature: Temperature for generation (0.0 to 1.0)
        max_tokens: Maximum tokens in response
        
    Returns:
        Generated text
    """
    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract and return the generated text
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        else:
            logger.warning("Empty response from OpenAI API")
            return ""
    except Exception as e:
        logger.error(f"Error generating OpenAI completion: {e}")
        return "" 