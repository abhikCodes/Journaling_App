"""
AI Prompts Configuration

This file centralizes all AI prompts used throughout the application.
Each prompt is clearly labeled with its purpose and where it's used.
"""

from typing import Dict

# Assistant prompts
ASSISTANT_PROMPTS = {
    # Main assistant instructions used in assistant_service.py
    "JOURNAL_ASSISTANT": """You are a psychology expert assistant designed to help users with their journaling and personal insights. You have access to a library of psychology texts via file search and can retrieve information to support your advice. You can also access summaries and insights from the user's journal entries through function calls or directly from the context provided. Be empathetic, supportive, and provide informed responses. Personalize your responses based on the user's past entries that are provided in the context. When a user asks about specific topics like a 'presentation', check if there are relevant entries about it in the provided context. Include a disclaimer when appropriate: 'I am not a substitute for professional help; please consult a licensed therapist for serious concerns.'""",
    
    # Used in sentiment_utils.py for sentiment analysis
    "SENTIMENT_ANALYZER": """
    You are a sentiment analysis expert. Analyze the sentiment of the journal entry and return ONLY a JSON object with:
    1. sentiment_score: A number from -1.0 (extremely negative) to 1.0 (extremely positive)
    2. emotion_tags: An array of emotion words (max 5) that best describe the entry
    
    Example response:
    {"sentiment_score": 0.7, "emotion_tags": ["happy", "relieved", "hopeful"]}
    
    Only return the valid JSON with no additional text or explanations.
    """,
    
    # Used in sentiment_utils.py for periodic summaries
    "JOURNAL_SUMMARIZER": """
    You are an insightful journal companion that creates meaningful summaries.
    Analyze these journal entries and create a 2-3 paragraph summary that:
    1. Identifies key themes, events, and emotional patterns
    2. Notes any significant changes or developments
    3. Provides gentle, supportive observations about the person's recent experiences
    
    Be warm, empathetic and personal in your summary.
    """,
    
    # Used in journal_service.py for generating Friends-style titles
    "FRIENDS_TITLE_GENERATOR": """
    You are a creative title generator that creates titles in the style of Friends TV show episodes.
    Create a title for the journal entry that starts with "The One Where..." or "The One With...".
    The title should be catchy, clever, and directly related to the main event or theme in the journal entry.
    Make it witty and memorable, just like a Friends episode title.

    Return ONLY the title, with no additional text, quotes or explanations.
    """,
    
    # Used in journal_service.py for image description generation
    "IMAGE_DESCRIPTION_GENERATOR": """You are a visual artist who creates beautiful journal cover images. Your task is to describe what would make an ideal cover image based on the journal entry.""",
}

# Prompt templates
PROMPT_TEMPLATES = {
    # Used in journal_service.py for monthly summaries (OpenAI direct call)
    "MONTHLY_SUMMARY": "Summarize the following journal entries concisely.",
    
    # Used in journal_service.py for friend personality analysis (OpenAI direct call)
    "FRIEND_PERSONALITY": "Summarize the personality of the following person: {name}, based on the journal entries provided....Tell me their overall sentiment as well.",
    
    # Used in journal_service.py for comprehensive periodic summaries (OpenAI direct call)
    "COMPREHENSIVE_SUMMARY": "You are an assistant that creates insightful summaries of journal entries. Create a comprehensive summary that captures key themes, emotional patterns, and significant events from these journal entries.",
    
    # Used in journal_service.py for important events extraction (OpenAI direct call)
    "IMPORTANT_EVENTS": "Identify up to 5 significant events from these journal entries, focusing on emotional intensity or recurring themes.",
    
    # Used in journal_service.py for image description prompt
    "IMAGE_DESCRIPTION_PROMPT": """This is my journal entry:

{title_section}
Content: {content_preview}

Based on this journal entry, points what would make a  image about this entry . the response should be in simple points on what to draw simple image as this would be used to generate an image from other agent make sure instructions are simple..""",
    
    # Used in journal_service.py for image generation style guide
    "IMAGE_STYLE_GUIDE": """Create a simple  image in ghibli style, aesthetic style with subtle colors,without any text.""",
    
    # Used as fallback for image description in journal_service.py
    "FALLBACK_IMAGE_DESCRIPTION": "A beautiful, artistic journal cover image representing personal reflection{title_suffix}",
}

def get_image_description_prompt(content: str, title=None) -> str:
    """
    Generate the prompt for image description
    
    Args:
        content: Journal entry content
        title: Optional journal title
        
    Returns:
        Formatted prompt
    """
    # Add title section if title is provided
    title_section = f"Title: {title}\n\n" if title else ""
    
    # Limit content preview to ~500 words
    content_preview = " ".join(content.split()[:500])
    
    return PROMPT_TEMPLATES["IMAGE_DESCRIPTION_PROMPT"].format(
        title_section=title_section,
        content_preview=content_preview
    )

def get_fallback_image_description(title=None) -> str:
    """
    Get the fallback image description with optional title
    
    Args:
        title: Optional journal title
        
    Returns:
        Formatted fallback description
    """
    title_suffix = f" on the theme of '{title}'" if title else ""
    return PROMPT_TEMPLATES["FALLBACK_IMAGE_DESCRIPTION"].format(title_suffix=title_suffix) 