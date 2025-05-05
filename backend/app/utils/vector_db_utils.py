from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import settings
import os
import logging
from typing import List, Dict, Any, Optional, Union
import uuid
import numpy as np
from datetime import datetime
from app.models import JournalEntry
import re

# Configure logging
logger = logging.getLogger(__name__)

# Try to import spaCy
try:
    import spacy
    # Load SpaCy model for entity recognition
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded SpaCy model: en_core_web_sm")
except Exception as e:
    logger.error(f"Error loading SpaCy model: {e}")
    nlp = None

# Initialize the embedding model
try:
    # Use a more powerful model for better semantic understanding
    model = SentenceTransformer('all-MiniLM-L6-v2')
    logger.info("Loaded SentenceTransformer model: all-MiniLM-L6-v2")
except Exception as e:
    logger.error(f"Error loading SentenceTransformer model: {e}")
    model = None

# Connect to Qdrant
client = QdrantClient(url=os.getenv("VECTORDB_URL", "http://vectordb:6333"))

# Constants
COLLECTION_NAME = "journal_entries"
VECTOR_SIZE = 384  # Dimension of all-MiniLM-L6-v2 embeddings

async def init_vector_db():
    """
    Initialize the vector database with the proper collection if it doesn't exist.
    """
    try:
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        
        if COLLECTION_NAME not in collection_names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Created collection {COLLECTION_NAME}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize vector database: {str(e)}")
        return False

def generate_embedding(text: str) -> List[float]:
    """
    Generate embeddings for a given text using SentenceTransformer.
    
    Args:
        text: The text to generate embeddings for
        
    Returns:
        A list of floats representing the embedding vector
    """
    try:
        if model is None:
            logger.error("Embedding model not initialized")
            return [0.0] * 384  # Default embedding size for all-MiniLM-L6-v2
        
        # Generate embedding
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return [0.0] * 384  # Return zeros as fallback

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score (float between -1 and 1)
    """
    try:
        # Convert to numpy arrays for efficient computation
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm_vec1 = np.linalg.norm(vec1)
        norm_vec2 = np.linalg.norm(vec2)
        
        # Handle zero division
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0
            
        similarity = dot_product / (norm_vec1 * norm_vec2)
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0

def normalize_score(score: float, min_score: float = 0.5) -> float:
    """
    Normalize a similarity score to be between 0 and 1.
    
    Args:
        score: Raw similarity score
        min_score: Minimum threshold for relevance
        
    Returns:
        Normalized score between 0 and 1
    """
    # Cap at 1.0 for maximum similarity
    if score > 1.0:
        return 1.0
    
    # Scale scores below min_score to 0
    if score < min_score:
        return 0.0
    
    # Linear scaling from min_score to 1.0
    return (score - min_score) / (1.0 - min_score)

async def search_similar_entries(
    user_id: int,
    query: str, 
    limit: int = 5, 
    min_score: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Search for journal entries similar to the query text using vector similarity.
    
    Args:
        user_id: ID of the user whose entries to search
        query: Search query text
        limit: Maximum number of results to return
        min_score: Minimum similarity score threshold
        
    Returns:
        List of dictionaries containing entry details and similarity scores
    """
    try:
        logger.info(f"Starting semantic search for user {user_id} with query: '{query}', limit: {limit}")
        
        # Generate embedding for the query
        query_embedding = generate_embedding(query)
        
        # Get all journal entries for this user
        entries = await JournalEntry.filter(user_id=user_id)
        logger.info(f"Found {len(entries)} total journal entries for user {user_id}")
        
        # Calculate similarity scores for each entry
        entry_scores = []
        for entry in entries:
            # Get entry embedding - check if the attribute exists first
            try:
                entry_embedding = entry.embedding if hasattr(entry, 'embedding') and entry.embedding else generate_embedding(entry.content)
            except AttributeError:
                # If embedding attribute doesn't exist, generate it from content
                entry_embedding = generate_embedding(entry.content)
            
            # Calculate similarity
            similarity = cosine_similarity(query_embedding, entry_embedding)
            
            # Normalize score
            normalized_score = normalize_score(similarity, min_score)
            
            # Skip entries below threshold
            if normalized_score > 0:
                entry_scores.append({
                    "id": entry.id,
                    "title": entry.title,
                    "content": entry.content,
                    "date": entry.date,
                    "similarity": normalized_score,
                    "user_id": entry.user_id
                })
        
        logger.info(f"Found {len(entry_scores)} entries above threshold score {min_score}")
        
        # Sort by similarity score (descending)
        sorted_entries = sorted(entry_scores, key=lambda x: x["similarity"], reverse=True)
        
        # Return top results
        results = sorted_entries[:limit]
        if results:
            logger.info(f"Top result score: {results[0]['similarity']:.4f}, user_id: {results[0].get('user_id')}")
            logger.info(f"Returning {len(results)} relevant entries")
        
        return results
    except Exception as e:
        logger.error(f"Error searching similar entries: {e}")
        logger.exception(e)  # Log the full stack trace
        return []

async def get_entry_embedding(entry_id: int) -> List[float]:
    """
    Get the embedding for a specific journal entry.
    If the entry doesn't have an embedding, generate and store one.
    
    Args:
        entry_id: ID of the journal entry
        
    Returns:
        List of floats representing the embedding vector
    """
    try:
        # Get the entry using Tortoise ORM
        entry = await JournalEntry.get_or_none(id=entry_id)
        
        if not entry:
            logger.error(f"Entry with ID {entry_id} not found")
            return [0.0] * 384
        
        # If embedding exists, return it
        if entry.embedding:
            return entry.embedding
        
        # Otherwise, generate and store embedding
        embedding = generate_embedding(entry.content)
        
        # Update entry with embedding
        entry.embedding = embedding
        await entry.save()
        
        return embedding
    except Exception as e:
        logger.error(f"Error getting/generating entry embedding: {e}")
        return [0.0] * 384

async def update_entry_embedding(entry_id: int) -> bool:
    """
    Update the embedding for a journal entry.
    
    Args:
        entry_id: ID of the journal entry
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Get the entry using Tortoise ORM
        entry = await JournalEntry.get_or_none(id=entry_id)
        
        if not entry:
            logger.error(f"Entry with ID {entry_id} not found")
            return False
        
        # Generate new embedding
        embedding = generate_embedding(entry.content)
        
        # Update entry with embedding
        entry.embedding = embedding
        await entry.save()
        
        return True
    except Exception as e:
        logger.error(f"Error updating entry embedding: {e}")
        return False

async def get_entry_by_id(entry_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a journal entry by ID.
    
    Args:
        entry_id: ID of the journal entry
        
    Returns:
        Dictionary containing entry details or None if not found
    """
    try:
        entry = await JournalEntry.get_or_none(id=entry_id)
        
        if not entry:
            return None
            
        return {
            "id": entry.id,
            "title": entry.title,
            "content": entry.content,
            "date": entry.date,
            "embedding": entry.embedding
        }
    except Exception as e:
        logger.error(f"Error getting entry by ID: {e}")
        return None

async def filter_entries_by_date(
    user_id: int,
    date_str: str,
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Filter journal entries by date range.
    
    Args:
        user_id: User ID to filter by
        date_str: Date string to parse (if start_date and end_date not provided)
        start_date: Start date for filtering (inclusive)
        end_date: End date for filtering (inclusive)
        
    Returns:
        List of dictionaries containing entry details
    """
    try:
        # If date_str is provided but not start/end dates, try to parse it
        if date_str and not (start_date and end_date):
            try:
                from dateutil.parser import parse as parse_date
                from datetime import timedelta
                from dateutil.relativedelta import relativedelta
                
                date_str = date_str.lower().strip()
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Handle special cases
                if date_str == "today":
                    start_date = today
                    end_date = start_date + timedelta(days=1)
                elif date_str == "yesterday":
                    start_date = today - timedelta(days=1)
                    end_date = start_date + timedelta(days=1)
                elif date_str == "this week":
                    start_date = today - timedelta(days=today.weekday())
                    end_date = start_date + timedelta(days=7)
                elif date_str == "last week":
                    start_date = today - timedelta(days=today.weekday() + 7)
                    end_date = start_date + timedelta(days=7)
                elif date_str == "this month":
                    start_date = today.replace(day=1)
                    if today.month == 12:
                        end_date = today.replace(year=today.year + 1, month=1, day=1)
                    else:
                        end_date = today.replace(month=today.month + 1, day=1)
                elif date_str == "last month":
                    if today.month == 1:
                        start_date = today.replace(year=today.year - 1, month=12, day=1)
                    else:
                        start_date = today.replace(month=today.month - 1, day=1)
                    end_date = today.replace(day=1)
                else:
                    # Handle month with day but without year (e.g., "August 20")
                    month_patterns = {
                        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
                        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
                        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, 
                        "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12
                    }
                    
                    month_found = False
                    extracted_month = None
                    extracted_day = None
                    
                    for month_name, month_num in month_patterns.items():
                        if month_name in date_str:
                            # Look for day number
                            day_pattern = fr"{month_name}\s+(\d{{1,2}})"
                            day_match = re.search(day_pattern, date_str)
                            if day_match:
                                day = int(day_match.group(1))
                                # Store extracted month and day for potential year-agnostic search later
                                extracted_month = month_num
                                extracted_day = day
                                
                                # Try current year first
                                try:
                                    start_date = datetime(today.year, month_num, day, 0, 0, 0)
                                    end_date = start_date + timedelta(days=1)
                                    month_found = True
                                    logger.info(f"Parsed date '{date_str}' as {start_date.strftime('%Y-%m-%d')}")
                                    break
                                except ValueError:
                                    # Try previous year if current year's date is invalid
                                    try:
                                        start_date = datetime(today.year - 1, month_num, day, 0, 0, 0)
                                        end_date = start_date + timedelta(days=1)
                                        month_found = True
                                        logger.info(f"Parsed date '{date_str}' as {start_date.strftime('%Y-%m-%d')} (previous year)")
                                        break
                                    except ValueError:
                                        logger.warning(f"Invalid date '{date_str}' - day {day} is not valid for month {month_name}")
                            
                            # Try "day Month" format (e.g., "20 August")
                            day_month_pattern = r"(\d{1,2})\s+(" + month_name + r")"
                            day_month_match = re.search(day_month_pattern, date_str)
                            if day_month_match:
                                day = int(day_month_match.group(1))
                                # Store extracted month and day for potential year-agnostic search later
                                extracted_month = month_num
                                extracted_day = day
                                
                                try:
                                    start_date = datetime(today.year, month_num, day, 0, 0, 0)
                                    end_date = start_date + timedelta(days=1)
                                    month_found = True
                                    logger.info(f"Parsed date '{date_str}' as {start_date.strftime('%Y-%m-%d')}")
                                    break
                                except ValueError:
                                    try:
                                        start_date = datetime(today.year - 1, month_num, day, 0, 0, 0)
                                        end_date = start_date + timedelta(days=1)
                                        month_found = True
                                        logger.info(f"Parsed date '{date_str}' as {start_date.strftime('%Y-%m-%d')} (previous year)")
                                        break
                                    except ValueError:
                                        logger.warning(f"Invalid date '{date_str}' - day {day} is not valid for month {month_name}")
                    
                    # If no month pattern matched, try generic date parsing
                    if not month_found:
                        # Try to parse as a specific date
                        try:
                            parsed_date = parse_date(date_str, fuzzy=True)
                            start_date = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                            end_date = start_date + timedelta(days=1)
                            logger.info(f"Parsed date '{date_str}' as {start_date.strftime('%Y-%m-%d')} using fuzzy parsing")
                        except Exception as e:
                            logger.error(f"Error parsing date string '{date_str}': {e}")
                            return []
            except Exception as e:
                logger.error(f"Error parsing date string '{date_str}': {e}")
                return []
        
        # Handle case when no dates were successfully parsed
        if not (start_date and end_date):
            logger.warning(f"Could not parse date from '{date_str}'")
            return []
            
        logger.info(f"Filtering entries for user {user_id} between {start_date} and {end_date}")
        
        # Start query with Tortoise ORM
        query = JournalEntry.filter(user_id=user_id)
        
        # Apply date filters - convert dates to correct format if needed
        if start_date:
            if isinstance(start_date, datetime):
                query = query.filter(date__gte=start_date)
            else:
                # Try to convert to datetime if it's a different type
                try:
                    start_dt = datetime.combine(start_date, datetime.min.time())
                    query = query.filter(date__gte=start_dt)
                except Exception as e:
                    logger.error(f"Error converting start_date to datetime: {e}")
        
        if end_date:
            if isinstance(end_date, datetime):
                query = query.filter(date__lte=end_date)
            else:
                try:
                    end_dt = datetime.combine(end_date, datetime.max.time())
                    query = query.filter(date__lte=end_dt)
                except Exception as e:
                    logger.error(f"Error converting end_date to datetime: {e}")
            
        # Execute query
        entries = await query
        logger.info(f"Found {len(entries)} entries for date range")
        
        # If no entries found and we have extracted month and day, try searching without year constraint
        if not entries and 'extracted_month' in locals() and extracted_month and extracted_day:
            logger.info(f"No entries found for specific year. Trying month/day search for month {extracted_month}, day {extracted_day}")
            
            # Get all entries for this user
            all_entries = await JournalEntry.filter(user_id=user_id)
            
            # Filter entries that match the same month and day
            matching_entries = []
            for entry in all_entries:
                entry_date = entry.date
                if entry_date and entry_date.month == extracted_month and entry_date.day == extracted_day:
                    matching_entries.append(entry)
            
            logger.info(f"Found {len(matching_entries)} entries with month {extracted_month}, day {extracted_day} across all years")
            
            # Format results
            results = []
            for entry in matching_entries:
                results.append({
                    "id": entry.id,
                    "title": entry.title,
                    "content": entry.content,
                    "date": entry.date,
                    "similarity": 0.95  # High default similarity for date-matched entries
                })
            
            return results
        
        # Format results from original query
        results = []
        for entry in entries:
            results.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "date": entry.date,
                "similarity": 0.95  # High default similarity for date-matched entries
            })
            
        return results
    except Exception as e:
        logger.error(f"Error filtering entries by date: {e}")
        logger.exception(e)  # Log the full stack trace
        return []

async def generate_embeddings_for_all() -> bool:
    """
    Generate embeddings for all journal entries that don't have them.
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Get entries without embeddings using Tortoise ORM
        entries = await JournalEntry.filter(embedding=None)
        
        logger.info(f"Generating embeddings for {len(entries)} entries")
        
        for entry in entries:
            # Generate embedding
            embedding = generate_embedding(entry.content)
            
            # Update entry
            entry.embedding = embedding
            await entry.save()
            
        return True
    except Exception as e:
        logger.error(f"Error generating embeddings for all entries: {e}")
        return False

async def keyword_search(
    user_id: int,
    query: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for journal entries containing specific keywords.
    
    Args:
        user_id: ID of the user whose entries to search
        query: The search query text
        limit: Maximum number of results to return
        
    Returns:
        List of dictionaries containing entry details and match scores
    """
    try:
        # Extract keywords from the query
        if nlp:
            doc = nlp(query)
            keywords = [token.text.lower() for token in doc 
                       if not token.is_stop and not token.is_punct and len(token.text) > 3]
        else:
            # Simple fallback without NLP
            keywords = [word.lower() for word in query.split() if len(word) > 3]
        
        if not keywords:
            # If no keywords extracted, use the original query words
            keywords = [word.lower() for word in query.split()]
        
        logger.info(f"Keyword search for user {user_id} with keywords: {keywords}")
        
        # Get all entries for the user using Tortoise ORM
        entries = await JournalEntry.filter(user_id=user_id)
        
        results = []
        for entry in entries:
            # Count how many keywords match
            content_lower = entry.content.lower()
            matches = sum(1 for kw in keywords if kw in content_lower)
            
            # Calculate match score (percentage of keywords matched)
            if len(keywords) > 0:
                score = matches / len(keywords)
            else:
                score = 0.0
                
            # Only include entries with at least one match
            if matches > 0:
                results.append({
                    "id": entry.id,
                    "title": entry.title,
                    "content": entry.content,
                    "date": entry.date,
                    "similarity": score  # Use similarity as the field name for consistency
                })
                
        # Sort by score (descending)
        sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)
        
        # Return top results
        return sorted_results[:limit]
    except Exception as e:
        logger.error(f"Error performing keyword search: {e}")
        return []

async def store_journal_entry(
    entry_id: int, 
    user_id: int,
    content: str, 
    date: str,
    tags: List[str] = None
) -> bool:
    """
    Store a journal entry in the vector database
    """
    try:
        # Generate embedding for the content
        embedding = generate_embedding(content)
        
        # Store in Qdrant with metadata
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=entry_id,
                    vector=embedding,
                    payload={
                        "user_id": user_id,
                        "content": content,
                        "date": date,
                        "tags": tags or []
                    }
                )
            ]
        )
        
        # Also update the embedding in the database
        entry = await JournalEntry.get_or_none(id=entry_id)
        if entry:
            entry.embedding = embedding
            await entry.save()
            
        return True
    except Exception as e:
        logger.error(f"Failed to store journal entry in vector DB: {str(e)}")
        return False

async def delete_journal_entry(entry_id: int) -> bool:
    """
    Delete a journal entry from the vector database
    """
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(
                points=[entry_id]
            )
        )
        return True
    except Exception as e:
        logger.error(f"Failed to delete journal entry from vector DB: {str(e)}")
        return False