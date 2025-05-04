from app.models import JournalEntry, PeriodicSummary, User
from app.config import settings
from openai import OpenAI
from datetime import datetime
import logging
from app.utils.sentiment_utils import analyze_sentiment
from app.utils.vector_db_utils import store_journal_entry
from app.utils.ai.manager import ai_manager
from app.config.ai import AIProvider
from app.config.prompts import ASSISTANT_PROMPTS, PROMPT_TEMPLATES, get_image_description_prompt, get_fallback_image_description
from app.utils.ai.logger import log_openai_direct_call
import os
import base64
import httpx
import json
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def get_monthly_summary(user):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(30)
    if not entries:
        return []
    contents = [entry.content for entry in entries]
    prompt = "\n".join(contents)
    
    system_prompt = PROMPT_TEMPLATES["MONTHLY_SUMMARY"]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    
    result = response.choices[0].message.content
    
    # Log the API call
    log_openai_direct_call(
        model="gpt-4o-mini",
        system_prompt=system_prompt,
        user_prompt=prompt[:500] + "..." if len(prompt) > 500 else prompt,
        response=result,
        prompt_type="monthly_summary",
        metadata={"user_id": user.id}
    )
    
    summaries = result.split("\n")
    return [summary.strip() for summary in summaries if summary.strip()]


async def get_important_events(user):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(30)
    if not entries:
        return []
    contents = [entry.content for entry in entries]
    prompt = "\n".join(contents)
    
    system_prompt = PROMPT_TEMPLATES["IMPORTANT_EVENTS"]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    
    result = response.choices[0].message.content
    
    # Log the API call
    log_openai_direct_call(
        model="gpt-4o-mini",
        system_prompt=system_prompt,
        user_prompt=prompt[:500] + "..." if len(prompt) > 500 else prompt,
        response=result,
        prompt_type="important_events",
        metadata={"user_id": user.id}
    )
    
    events = result.split("\n")
    return [event.strip() for event in events if event.strip()]


async def get_friend_personality(user, f_name):
    entries = await JournalEntry.filter(user=user).order_by("-date").limit(30)
    if not entries:
        return []
    
    contents = [entry.content for entry in entries]

    if not any(f_name.lower() in text.lower() for text in contents):
        return ["Friend not present"]
    
    prompt = "\n".join(contents)
    
    system_prompt = PROMPT_TEMPLATES["FRIEND_PERSONALITY"].format(name=f_name)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    
    result = response.choices[0].message.content
    
    # Log the API call
    log_openai_direct_call(
        model="gpt-4o-mini",
        system_prompt=system_prompt,
        user_prompt=prompt[:500] + "..." if len(prompt) > 500 else prompt,
        response=result,
        prompt_type="friend_personality",
        metadata={"user_id": user.id, "friend_name": f_name}
    )
    
    summaries = result.split("\n")
    return [summary.strip() for summary in summaries if summary.strip()]

async def check_and_generate_summary(user: User):
    """
    Check if it's time to generate a new periodic summary (after every 15 entries)
    and create one if needed
    """
    try:
        # Calculate how many entries since last summary
        entries_since_last_summary = user.entry_count - user.last_summary_count
        
        logger.info(f"User {user.id} has {entries_since_last_summary} entries since last summary")
        
        # Generate summary after every 15 entries
        if entries_since_last_summary >= 15:
            logger.info(f"Generating new summary for user {user.id} after {entries_since_last_summary} entries")
            
            # Get the entries since the last summary
            entries = await JournalEntry.filter(user=user).order_by("-date").limit(entries_since_last_summary)
            
            if not entries:
                logger.warning(f"No entries found for user {user.id} despite entry count")
                return
            
            # Get date range
            entries_list = list(entries)
            start_date = min(entry.date for entry in entries_list)
            end_date = max(entry.date for entry in entries_list)
            
            # Prepare content for summarization
            contents = [entry.content for entry in entries_list]
            prompt = "\n".join(contents)
            
            # Generate summary using AI
            try:
                system_prompt = PROMPT_TEMPLATES["COMPREHENSIVE_SUMMARY"]
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                
                summary_content = response.choices[0].message.content.strip()
                
                # Log the API call
                log_openai_direct_call(
                    model="gpt-4o-mini",
                    system_prompt=system_prompt,
                    user_prompt=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                    response=summary_content,
                    prompt_type="comprehensive_summary",
                    metadata={
                        "user_id": user.id,
                        "entry_count": entries_since_last_summary,
                        "date_range": f"{start_date} to {end_date}"
                    }
                )
                
                # Create and save the summary
                summary = PeriodicSummary(
                    user=user,
                    start_date=start_date,
                    end_date=end_date,
                    content=summary_content,
                    entry_count=entries_since_last_summary
                )
                await summary.save()
                
                # Update the user's last summary count
                user.last_summary_count = user.entry_count
                await user.save()
                
                logger.info(f"Successfully created periodic summary for user {user.id}")
                return summary
                
            except Exception as e:
                logger.error(f"Error generating summary with AI: {str(e)}")
                return None
        
        return None
    except Exception as e:
        logger.error(f"Error in check_and_generate_summary: {str(e)}")
        return None

async def generate_cover_image(content: str, title: Optional[str] = None) -> Optional[str]:
    """
    Generate a cover image for a journal entry using AI
    
    Args:
        content: The journal entry content to generate an image for
        title: Optional title to include in the prompt
        
    Returns:
        URL to the generated image or None if generation failed
    """
    try:
        # STEP 1: Generate an image description using existing AI manager
        logger.info("Step 1: Generating image description using AI manager")
        
        # Build the prompt for the LLM using the centralized prompt template
        description_prompt = get_image_description_prompt(content, title)
        
        # Get image description using AI manager
        try:
            logger.info("Creating image description assistant")
            
            # Create a temporary assistant for image description
            assistant = await ai_manager.create_assistant(
                name="Image Description Generator",
                instructions=ASSISTANT_PROMPTS["IMAGE_DESCRIPTION_GENERATOR"]
            )
            
            # Get the response using AI manager
            logger.info("Calling AI manager to generate image description")
            response_data = await ai_manager.get_response(
                user_message=description_prompt,
                assistant_id=assistant["id"]
            )
            
            image_description = response_data["response"].strip()
            logger.info(f"Generated image description: {image_description[:150]}...")
            
        except Exception as e:
            logger.error(f"Error generating image description: {str(e)}")
            # Fall back to a simple description
            logger.warning("Using fallback image description")
            image_description = get_fallback_image_description(title)
        
        # STEP 2: Generate the actual image using the description
        logger.info("Step 2: Generating image using AI manager")
        
        # Construct the final prompt
        style_guide = PROMPT_TEMPLATES["IMAGE_STYLE_GUIDE"]
        final_prompt = f"{image_description}. {style_guide}"
        
        # Ensure prompt isn't too long
        if len(final_prompt) > 1000:
            final_prompt = final_prompt[:997] + "..."
            
        logger.info(f"Final image prompt: {final_prompt[:150]}...")
        
        # Generate the image using AI manager
        image_url = await ai_manager.generate_image(
            prompt=final_prompt,
            size="1024x1024"
        )
        
        if not image_url:
            logger.warning("Failed to generate image: No URL returned")
            return None
            
        # If the image is hosted externally, download it and store locally
        if image_url.startswith(("http://", "https://")):
            logger.info(f"External image URL received. Downloading from: {image_url[:60]}...")
            
            # Define the uploads directory - IMPORTANT: Make sure this matches the directory structure in main.py
            UPLOAD_DIR = "uploads/journal_images"
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            logger.info(f"Using upload directory: {UPLOAD_DIR}")
            
            # Generate a unique filename that matches the user upload pattern
            # Use a fake user_id of 0 for AI-generated images to keep them separate
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"0_ai_cover_{timestamp}.png"
            filepath = os.path.join(UPLOAD_DIR, filename)
            logger.info(f"Generated filename: {filename}")
            
            # Download the image
            logger.info("Initiating HTTP request to download image")
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                status_code = response.status_code
                logger.info(f"Download response status code: {status_code}")
                
                if status_code != 200:
                    logger.error(f"Failed to download image: HTTP {status_code}")
                    logger.error(f"Response headers: {response.headers}")
                    logger.error(f"Response text: {response.text[:200]}")
                    return None  # Return None instead of the original URL since it won't work in Docker
                
                # Save the image
                content_length = len(response.content)
                logger.info(f"Downloaded image size: {content_length} bytes")
                
                try:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    
                    logger.info(f"Successfully saved image to {filepath}")
                    
                    # Verify the file exists and has content
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        logger.info(f"File verification successful: {filepath} exists with {os.path.getsize(filepath)} bytes")
                    else:
                        logger.error(f"File verification failed: File missing or empty at {filepath}")
                        return None
                        
                except Exception as write_error:
                    logger.error(f"Error writing file: {str(write_error)}")
                    return None
                
                # Return a relative URL path that will be properly handled by the API routes
                # This will be prefixed with the correct base URL by the route handlers
                relative_url = f"/uploads/journal_images/{filename}"
                logger.info(f"Returning relative URL: {relative_url}")
                return relative_url
        
        # This branch shouldn't be reached in normal operation
        logger.warning(f"Unexpected image URL format: {image_url}")
        return None
            
    except Exception as e:
        logger.error(f"Error generating cover image: {str(e)}")
        logger.exception("Full traceback:")
        return None
