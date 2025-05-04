from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from app.schemas import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, TitleGenerationRequest, CoverImageRequest
from app.models import JournalEntry, User, PeriodicSummary
from app.routes.auth import get_current_user
from app.utils.vector_db_utils import store_journal_entry, delete_journal_entry, search_similar_entries
from app.utils.sentiment_utils import analyze_sentiment
from app.services.journal_service import check_and_generate_summary, generate_cover_image
from app.utils.ai.manager import ai_manager
from app.config.prompts import ASSISTANT_PROMPTS
import logging
import os
import shutil
from uuid import uuid4
from fastapi.encoders import jsonable_encoder

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Checkpoint storage directory
CHECKPOINT_DIR = "./checkpoints"
if not os.path.exists(CHECKPOINT_DIR):
    os.makedirs(CHECKPOINT_DIR)

@router.post("/genisis")
async def genesis_upload(mode: str = Form(..., description="'next15' to process next 15 entries, 'all' to process entire CSV"), file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """
    Bulk upload journal entries from CSV. Modes:
    - next15: process next 15 entries since last checkpoint
    - all: process all entries from CSV
    """
    # Read .csv file
    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode()), converters={"tags": json.loads})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV or tags format")

    total = len(df)

    # We create a checkpoint file for the user
    checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{user.id}_{file.filename}.chk")

    # Determine start index
    if os.path.exists(checkpoint_file) and mode == "next15":
        with open(checkpoint_file, 'r') as f:
            start_idx = int(f.read().strip() or 0)
    else:
        start_idx = 0

    if mode == "next15":
        end_idx = min(start_idx + 15, total)
    elif mode == "all":
        end_idx = total
    else:
        raise HTTPException(status_code=400, detail="Mode must be 'next15' or 'all'")
    
    tasks = []
    for idx in range(start_idx, end_idx):
        row = df.iloc[idx]
        entry_in = JournalEntryCreate(
            date=row["date"],
            content=row["content"],
            tags=row["tags"]
        )
        tasks.append(create_entry(entry=entry_in, user=user))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed = 0
    for idx, res in enumerate(results, start=start_idx):
        if isinstance(res, Exception):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create entry at index {idx}: {res}"
            )
        processed += 1

    # write checkpoint
    next_idx = end_idx if mode == "next15" else total

    if next_idx >= total:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
    else:
        with open(checkpoint_file, 'w') as f:
            f.write(str(next_idx))

    return {
        "processed": processed, 
        "next_index": next_idx, 
        "total": total
    }
# Configure upload directory
UPLOAD_DIR = "uploads/journal_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Function to save uploaded image
async def save_upload_file(upload_file: UploadFile, user_id: int, request: Request) -> str:
    """Save an uploaded file and return the file path"""
    # Create unique filename to avoid collisions
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{user_id}_{uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    # Return the URL using the StaticFiles mount path
    return f"/uploads/journal_images/{unique_filename}"

# Function to delete image file
async def delete_image_file(image_url: str):
    """Delete an image file if it exists"""
    if not image_url:
        return
        
    # Extract the path from the URL
    try:
        # Get the file path relative to the uploads directory
        path_parts = image_url.split("/uploads/")
        if len(path_parts) == 2:
            relative_path = path_parts[1]
            file_path = os.path.join("uploads", relative_path)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted image file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting image file: {str(e)}")

async def validate_journal_entry(user: User, entry_date: date, content: str, entry_id: Optional[int] = None):
    """
    Validate a journal entry based on date and content constraints.
    Will raise HTTPException if validation fails.
    """
    # 1. Check for empty entries or entries with less than 20 words
    if not content or len(content.split()) < 20:
        word_count = len(content.split()) if content else 0
        raise HTTPException(
            status_code=400,
            detail=f"Journal entries must contain at least 20 words. Current word count: {word_count}"
        )
    
    # 2. Check for future entries
    today = date.today()
    if entry_date > today:
        raise HTTPException(
            status_code=400,
            detail="Cannot create entries for future dates"
        )
    
    # 3. Check for duplicate dates (only for the same user)
    existing_query = JournalEntry.filter(user=user, date=entry_date)
    if entry_id:  # For updates, exclude the current entry
        existing_query = existing_query.filter(id__not=entry_id)
    
    existing_entry = await existing_query.first()
    if existing_entry:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a journal entry for {entry_date}. Please edit the existing entry instead."
        )

@router.post("/entries", response_model=JournalEntryResponse)
async def create_entry(
    request: Request,
    date: str = Form(...),
    content: str = Form(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form("[]"),
    image: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user)
):
    # Convert string date to date object
    entry_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    # Parse tags from JSON string
    import json
    tags_list = json.loads(tags) if tags else []
    
    # Validate the entry
    await validate_journal_entry(user, entry_date, content)
    
    # Analyze sentiment
    sentiment_score, emotion_tags = await analyze_sentiment(content)
    
    # Save image if provided
    image_url = None
    if image:
        try:
            image_url = await save_upload_file(image, user.id, request)
        except Exception as e:
            logger.error(f"Failed to save image: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save image")
    
    # Create the entry
    new_entry = await JournalEntry.create(
        user=user,
        title=title,
        date=entry_date,
        content=content,
        tags=tags_list,
        sentiment_score=sentiment_score,
        emotion_tags=emotion_tags,
        image_url=image_url
    )
    
    # Store in vector database
    try:
        await store_journal_entry(
            entry_id=new_entry.id,
            user_id=user.id,
            content=content,
            date=str(entry_date),
            tags=tags_list
        )
    except Exception as e:
        logger.error(f"Failed to store entry in vector DB: {str(e)}")
    
    # Update user's entry count
    user.entry_count += 1
    await user.save()
    
    # Check if we need to generate a periodic summary (every 15 entries)
    try:
        summary = await check_and_generate_summary(user)
        if summary:
            logger.info(f"Generated new periodic summary for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to generate periodic summary: {str(e)}")
    
    # Ensure image URL has the correct base URL
    base_url = str(request.base_url).rstrip('/')
    final_image_url = f"{base_url}{image_url}" if image_url and image_url.startswith('/') else image_url
    
    return JournalEntryResponse(
        id=new_entry.id,
        title=new_entry.title,
        date=new_entry.date,
        content=new_entry.content,
        tags=new_entry.tags,
        sentiment_score=sentiment_score,
        emotion_tags=emotion_tags,
        image_url=final_image_url
    )

@router.get("/entries", response_model=List[JournalEntryResponse])
async def list_entries(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user: User = Depends(get_current_user)
):
    query = JournalEntry.filter(user=user)
    if search:
        query = query.filter(content__icontains=search)
    if tag:
        query = query.filter(tags__contains=[tag])
    if start_date:
        query = query.filter(date__gte=start_date)
    if end_date:
        query = query.filter(date__lte=end_date)
    entries = await query.offset(skip).limit(limit)
    
    # Ensure image URLs have the correct base URL
    base_url = str(request.base_url).rstrip('/')
    
    return [
      JournalEntryResponse(
        id=e.id, 
        title=e.title,
        date=e.date, 
        content=e.content, 
        tags=e.tags,
        sentiment_score=e.sentiment_score,
        emotion_tags=e.emotion_tags,
        # Prefix relative image URLs with base URL if present
        image_url=f"{base_url}{e.image_url}" if e.image_url and e.image_url.startswith('/') else e.image_url
      )
      for e in entries
    ]

@router.get("/entries/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(
    entry_id: int,
    request: Request,
    user: User = Depends(get_current_user)
):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Ensure image URL has the correct base URL
    base_url = str(request.base_url).rstrip('/')
    image_url = f"{base_url}{entry.image_url}" if entry.image_url and entry.image_url.startswith('/') else entry.image_url
    
    return JournalEntryResponse(
        id=entry.id,
        title=entry.title,
        date=entry.date,
        content=entry.content,
        tags=entry.tags,
        sentiment_score=entry.sentiment_score,
        emotion_tags=entry.emotion_tags,
        image_url=image_url
    )

@router.put("/entries/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(
    entry_id: int,
    request: Request,
    date: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user)
):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Prepare update data
    update_data = {}
    
    # Process date if provided
    if date:
        update_data["date"] = datetime.strptime(date, "%Y-%m-%d").date()
    
    # Process content if provided
    if content:
        update_data["content"] = content
    
    # Process title if provided
    if title:
        update_data["title"] = title
    
    # Process tags if provided
    if tags:
        import json
        update_data["tags"] = json.loads(tags)
    
    # Validate entry if date or content is being updated
    if "date" in update_data or "content" in update_data:
        date_to_validate = update_data.get("date", entry.date)
        content_to_validate = update_data.get("content", entry.content)
        await validate_journal_entry(
            user=user, 
            entry_date=date_to_validate, 
            content=content_to_validate, 
            entry_id=entry_id
        )
    
    # If content is updated, re-analyze sentiment
    if "content" in update_data:
        sentiment_score, emotion_tags = await analyze_sentiment(update_data["content"])
        update_data["sentiment_score"] = sentiment_score
        update_data["emotion_tags"] = emotion_tags
    
    # Process image if provided
    if image:
        try:
            # Delete previous image if exists
            if entry.image_url:
                await delete_image_file(entry.image_url)
            
            # Save new image
            update_data["image_url"] = await save_upload_file(image, user.id, request)
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process image")
    
    # Update entry
    await entry.update_from_dict(update_data)
    await entry.save()
    
    # Update in vector database if content or tags were changed
    if "content" in update_data or "tags" in update_data:
        try:
            await store_journal_entry(
                entry_id=entry.id,
                user_id=user.id,
                content=entry.content,
                date=str(entry.date),
                tags=entry.tags
            )
        except Exception as e:
            logger.error(f"Failed to update entry in vector DB: {str(e)}")
    
    # Ensure image URL has the correct base URL
    base_url = str(request.base_url).rstrip('/')
    final_image_url = f"{base_url}{entry.image_url}" if entry.image_url and entry.image_url.startswith('/') else entry.image_url
    
    return JournalEntryResponse(
        id=entry.id,
        title=entry.title,
        date=entry.date,
        content=entry.content,
        tags=entry.tags,
        sentiment_score=entry.sentiment_score,
        emotion_tags=entry.emotion_tags,
        image_url=final_image_url
    )

@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: int, user: User = Depends(get_current_user)):
    entry = await JournalEntry.get_or_none(id=entry_id, user=user)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    # Delete associated image if it exists
    if entry.image_url:
        try:
            await delete_image_file(entry.image_url)
        except Exception as e:
            logger.error(f"Failed to delete image file: {str(e)}")
    
    # Delete from vector database
    try:
        await delete_journal_entry(entry_id=entry.id)
    except Exception as e:
        logger.error(f"Failed to delete entry from vector DB: {str(e)}")
    
    await entry.delete()
    return {"message": "Entry deleted"}

@router.get("/search", response_model=List[JournalEntryResponse])
async def semantic_search(query: str, limit: int = 5, user: User = Depends(get_current_user)):
    """
    Search for journal entries semantically similar to the query
    """
    try:
        # Perform semantic search in vector DB
        results = await search_similar_entries(
            user_id=user.id,
            query=query,
            limit=limit
        )
        
        # Format results
        response = []
        for result in results:
            # Get full entry from DB to include title
            entry = await JournalEntry.get(id=result["id"])
            response.append(
                JournalEntryResponse(
                    id=result["id"],
                    title=entry.title,
                    date=result["date"],
                    content=result["content"],
                    tags=result["tags"]
                )
            )
        
        return response
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Semantic search failed")

@router.post("/generate-title")
async def generate_title(request: TitleGenerationRequest, user: User = Depends(get_current_user)):
    """
    Generate a title for a journal entry in the style of Friends TV show episodes
    """
    content = request.content.strip()
    
    # Define minimum word count threshold
    MIN_WORDS = 20
    
    # Check if content meets minimum word count
    word_count = len(content.split())
    if word_count < MIN_WORDS:
        raise HTTPException(
            status_code=400, 
            detail=f"Your journal entry needs at least {MIN_WORDS} words to generate a title. Current word count: {word_count}"
        )
    
    try:
        # Get the instructions from centralized prompts
        instructions = ASSISTANT_PROMPTS["FRIENDS_TITLE_GENERATOR"]
        
        # Create a temporary assistant for this task
        assistant = await ai_manager.create_assistant(
            name="Friends Title Generator",
            instructions=instructions
        )
        
        # Send the content as user message - ai_manager will create a thread internally
        response_data = await ai_manager.get_response(
            user_message=content,
            assistant_id=assistant["id"]
        )
        
        title = response_data["response"].strip()
        return {"title": title}
        
    except Exception as e:
        logger.error(f"Title generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate title")

# New endpoint for AI cover image generation
@router.post("/generate-cover-image")
async def create_cover_image(
    request_body: CoverImageRequest,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    Generate an AI cover image for a journal entry based on its content and title.
    
    Args:
        request_body: Request containing content and optional title
        request: The FastAPI request object
        user: Current authenticated user
        
    Returns:
        JSON with the URL of the generated image
    """
    if not request_body.content or len(request_body.content.split()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Content must contain at least 20 words to generate a meaningful image"
        )
    
    try:
        # Generate the cover image
        image_url = await generate_cover_image(request_body.content, request_body.title)
        
        if not image_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate cover image. Please try again later."
            )
        
        # Ensure image URL has the correct base URL
        base_url = str(request.base_url).rstrip('/')
        final_image_url = f"{base_url}{image_url}" if image_url and image_url.startswith('/') else image_url
        
        return {"image_url": final_image_url}
    
    except Exception as e:
        logger.error(f"Error generating cover image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )
