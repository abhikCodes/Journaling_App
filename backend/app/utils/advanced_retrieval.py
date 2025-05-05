"""
Advanced retrieval system for journal entries.

This module implements an enhanced retrieval pipeline for finding relevant journal entries
based on user queries. It includes:

1. Improved embedding with better models
2. Query type detection and specialized handling
3. Entity extraction and date filtering
4. Hybrid search combining semantic and keyword matching
5. Relevance scoring and ranking optimization
6. Query expansion for broader matching
7. Content summarization for more relevant context
"""

import re
import logging
import spacy
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
import numpy as np
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

from app.models import JournalEntry
from app.utils.vector_db_utils import (
    generate_embedding, 
    cosine_similarity, 
    normalize_score,
    search_similar_entries,
    keyword_search,
    filter_entries_by_date
)
from app.utils.openai_utils import generate_openai_completion
from app.config.prompts import PROMPT_TEMPLATES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MIN_SIMILARITY_SCORE = 0.5
MAX_RESULTS = 10
DATE_PATTERNS = [
    r'\b(?:on|in|during|at)\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})',  # on January 1st, 2023
    r'\b(?:on|in|during|at)\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4})',  # on 1st January, 2023
    r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',  # 01/15/2023
    r'\b(\d{4}-\d{1,2}-\d{1,2})\b',  # 2023-01-15
    r'\b(?:last|this|next)\s+(week|month|year)\b',  # last week, this month
    r'\b(\d{1,2})\s+(?:days|weeks|months|years)\s+ago\b',  # 3 days ago
    r'\byesterday\b',  # yesterday
    r'\btoday\b',  # today
]
TEMPORAL_KEYWORDS = [
    'yesterday', 'today', 'tomorrow', 'last week', 'this week', 'next week', 
    'last month', 'this month', 'next month', 'last year', 'this year', 'next year'
]
QUERY_TYPES = [
    'date', 'person', 'event', 'feeling', 'topic', 'reflection'
]

# Load SpaCy model for entity recognition
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded SpaCy model: en_core_web_sm")
except Exception as e:
    logger.error(f"Error loading SpaCy model: {e}")
    nlp = None

def detect_query_type(query: str) -> str:
    """
    Detect the type of query: date, topic, person, location, general.
    
    Args:
        query: The user query string
        
    Returns:
        The query type as a string
    """
    query = query.lower()
    
    # Check for date queries
    date_patterns = [
        r"(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)\s+\d{1,2}",  # Month name followed by day
        r"\d{1,2}\s+(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|sep(t(ember)?)?|oct(ober)?|nov(ember)?|dec(ember)?)",  # Day followed by month name
        r"\d{4}-\d{1,2}-\d{1,2}",  # YYYY-MM-DD
        r"\d{1,2}/\d{1,2}/\d{2,4}",  # MM/DD/YY or MM/DD/YYYY or DD/MM/YY or DD/MM/YYYY
        r"\d{1,2}-\d{1,2}-\d{2,4}",  # MM-DD-YY or MM-DD-YYYY or DD-MM-YY or DD-MM-YYYY
        r"\b(last|this|next)\s+(week|month|year)\b",  # Relative date expressions
        r"\b(yesterday|today|tomorrow)\b",  # Day references
        r"\b\d{1,2}\s+days?\s+ago\b",  # X days ago
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",  # Days of the week
    ]
    
    # Define keywords that indicate a date query
    date_keywords = [
        "when", "date", "day", "time", "month", "year", "happened", "occur", "ago",
        "on the", "on", "at", "in", "during", "since", "yesterday", "today", "last week", 
        "last month", "last year", "this week", "this month", "this year", "next"
    ]
    
    # Check for exact date patterns in the query
    for pattern in date_patterns:
        if re.search(pattern, query):
            logger.info(f"Detected date query with pattern: '{query}'")
            return "date"
    
    # If no direct pattern, check for date-related keywords
    for keyword in date_keywords:
        if keyword in query.split() or f" {keyword} " in f" {query} ":
            # Check if there are month names in the query as another strong indicator
            month_names = [
                "january", "february", "march", "april", "may", "june", "july",
                "august", "september", "october", "november", "december",
                "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"
            ]
            
            for month in month_names:
                if month in query:
                    logger.info(f"Detected date query with month name: '{query}'")
                    return "date"
            
            # Special case for "ago" which almost always implies a date
            if "ago" in query:
                logger.info(f"Detected date query with 'ago': '{query}'")
                return "date"
                
            # Special case for specific date keywords that strongly indicate a date query
            strong_date_words = ["yesterday", "today", "tomorrow", "last week", "this week", "next week"]
            for strong_word in strong_date_words:
                if strong_word in query:
                    logger.info(f"Detected date query with '{strong_word}': '{query}'")
                    return "date"
                    
            # Check if there are day numbers (1-31) with surrounding spaces indicating a specific day
            day_pattern = r"\b(3[01]|[12][0-9]|[1-9])(st|nd|rd|th)?\b"
            if re.search(day_pattern, query):
                logger.info(f"Detected date query with day number: '{query}'")
                return "date"
    
    # If we're still here, check for other query types
    
    # Check for person queries
    person_keywords = ["who", "person", "people", "friend", "family", "colleague", "contact", "group"]
    for keyword in person_keywords:
        if keyword in query.split() or f" {keyword} " in f" {query} ":
            logger.info(f"Detected person query: '{query}'")
            return "person"
    
    # Check for location queries
    location_keywords = ["where", "place", "location", "at", "in", "near", "around", "venue", "destination"]
    for keyword in location_keywords:
        if keyword in query.split() or f" {keyword} " in f" {query} ":
            logger.info(f"Detected location query: '{query}'")
            return "location"
    
    # Default to topic if no specific type detected
    logger.info(f"Detected topic query (default): '{query}'")
    return "topic"

def extract_entities(query: str) -> Dict[str, List[str]]:
    """
    Extract named entities from the query.
    
    Args:
        query: The user's search query
        
    Returns:
        Dictionary of entity types and their values
    """
    entities = {
        'dates': [],
        'people': [],
        'locations': [],
        'organizations': []
    }
    
    if not nlp:
        logger.warning("SpaCy model not loaded, skipping entity extraction")
        return entities
    
    try:
        # Process with SpaCy
        doc = nlp(query)
        
        # Extract entities
        for ent in doc.ents:
            if ent.label_ == 'DATE' or ent.label_ == 'TIME':
                entities['dates'].append(ent.text)
            elif ent.label_ == 'PERSON':
                entities['people'].append(ent.text)
            elif ent.label_ == 'GPE' or ent.label_ == 'LOC':
                entities['locations'].append(ent.text)
            elif ent.label_ == 'ORG':
                entities['organizations'].append(ent.text)
        
        # Look for temporal expressions
        for keyword in TEMPORAL_KEYWORDS:
            if keyword in query.lower():
                entities['dates'].append(keyword)
                
        # Extract date patterns using regular expressions
        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, query)
            entities['dates'].extend(matches)
        
        # Enhanced date extraction for month-day formats
        month_names = [
            "january", "february", "march", "april", "may", "june", 
            "july", "august", "september", "october", "november", "december",
            "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"
        ]
        
        query_lower = query.lower()
        for month in month_names:
            if month in query_lower:
                # Look for patterns like "Month day" or "day Month"
                month_day_pattern = fr"{month}\s+(\d{{1,2}})"
                day_month_pattern = r"(\d{1,2})\s+(" + month + r")"
                
                month_day_matches = re.findall(month_day_pattern, query_lower)
                for day in month_day_matches:
                    entities['dates'].append(f"{month} {day}")
                
                day_month_matches = re.findall(day_month_pattern, query_lower)
                for match in day_month_matches:
                    if len(match) >= 2:
                        entities['dates'].append(f"{match[0]} {match[1]}")
        
        # Deduplicate dates
        if entities['dates']:
            entities['dates'] = list(set(entities['dates']))
        
        # Log extracted entities for debugging
        if entities['dates']:
            logger.info(f"Extracted date entities from query: {entities['dates']}")
        
        return entities
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        return entities

async def expand_query(query: str) -> str:
    """
    Expand the query with related terms to improve recall.
    
    Args:
        query: The user's search query
        
    Returns:
        Expanded query with related terms
    """
    try:
        # Simple expansion by adding synonyms for common terms
        expansions = {
            "happy": "happy joyful glad pleased delighted content",
            "sad": "sad unhappy depressed down blue gloomy",
            "angry": "angry upset mad furious enraged irritated",
            "worried": "worried anxious concerned nervous stressed",
            "tired": "tired exhausted fatigued drained sleepy",
            "excited": "excited thrilled enthusiastic eager",
            "scared": "scared afraid frightened terrified fearful",
            "confused": "confused puzzled perplexed bewildered",
            "busy": "busy occupied swamped overwhelmed",
            "relaxed": "relaxed calm peaceful tranquil chill"
        }
        
        # Simple implementation - just add some common synonyms
        expanded = query
        for term, expansion in expansions.items():
            if term.lower() in query.lower():
                expanded += f" {expansion}"
                
        # If no expansions were made, just return the original query
        if expanded == query:
            expanded_terms = []
            words = query.lower().split()
            for word in words:
                if len(word) > 3 and not word.startswith(('how', 'what', 'when', 'where', 'who', 'why')):
                    expanded_terms.append(word)
            
            if expanded_terms:
                expanded = f"{query} {' '.join(expanded_terms)}"
        
        logger.info(f"Expanded query from '{query}' to '{expanded}'")
        return expanded
    except Exception as e:
        logger.error(f"Error expanding query: {e}")
        return query  # Return original query on error

def parse_date_expression(date_expr: str) -> Optional[Tuple[datetime, datetime]]:
    """
    Parse a date expression and return a date range.
    
    Args:
        date_expr: Date expression to parse
        
    Returns:
        Tuple of (start_date, end_date) or None if unable to parse
    """
    try:
        if not date_expr:
            return None
            
        date_expr = date_expr.lower().strip()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Handle relative date expressions
        if date_expr == 'today':
            return (today, today + timedelta(days=1) - timedelta(seconds=1))
        elif date_expr == 'yesterday':
            return (today - timedelta(days=1), today - timedelta(seconds=1))
        elif date_expr == 'this week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=7) - timedelta(seconds=1)
            return (start, end)
        elif date_expr == 'last week':
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=7) - timedelta(seconds=1)
            return (start, end)
        elif date_expr == 'this month':
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(seconds=1)
            return (start, end)
        elif date_expr == 'last month':
            if today.month == 1:
                start = today.replace(year=today.year - 1, month=12, day=1)
            else:
                start = today.replace(month=today.month - 1, day=1)
            end = today.replace(day=1) - timedelta(seconds=1)
            return (start, end)
        
        # Handle "X days/weeks/months ago"
        ago_match = re.match(r'(\d+)\s+(day|week|month|year)s?\s+ago', date_expr)
        if ago_match:
            num = int(ago_match.group(1))
            unit = ago_match.group(2)
            
            if unit == 'day':
                start = today - timedelta(days=num)
                end = start + timedelta(days=1) - timedelta(seconds=1)
            elif unit == 'week':
                start = today - timedelta(weeks=num)
                end = start + timedelta(days=7) - timedelta(seconds=1)
            elif unit == 'month':
                start = today - relativedelta(months=num)
                end = start + relativedelta(months=1) - timedelta(seconds=1)
            elif unit == 'year':
                start = today - relativedelta(years=num)
                end = start + relativedelta(years=1) - timedelta(seconds=1)
            else:
                return None
                
            return (start, end)
                
        # Enhanced handling of month with day but without year
        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, 
            "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        # Check for "Month day" format (like "August 20")
        for month_name, month_num in month_names.items():
            if month_name in date_expr:
                # Look for day after month name
                pattern = fr"{month_name}\s+(\d{{1,2}})"
                day_match = re.search(pattern, date_expr)
                if day_match:
                    day = int(day_match.group(1))
                    # Create date with current year
                    try:
                        date_obj = datetime(today.year, month_num, day, 0, 0, 0)
                        return (date_obj, date_obj + timedelta(days=1) - timedelta(seconds=1))
                    except ValueError:
                        # Try previous year if date is invalid (like Feb 29 in non-leap year)
                        try:
                            date_obj = datetime(today.year - 1, month_num, day, 0, 0, 0)
                            return (date_obj, date_obj + timedelta(days=1) - timedelta(seconds=1))
                        except ValueError:
                            pass
                
                # Look for day before month name (like "20 August")
                pattern = r"(\d{1,2})\s+(" + month_name + r")"
                day_match = re.search(pattern, date_expr)
                if day_match:
                    day = int(day_match.group(1))
                    try:
                        date_obj = datetime(today.year, month_num, day, 0, 0, 0)
                        return (date_obj, date_obj + timedelta(days=1) - timedelta(seconds=1))
                    except ValueError:
                        # Try previous year if date is invalid
                        try:
                            date_obj = datetime(today.year - 1, month_num, day, 0, 0, 0)
                            return (date_obj, date_obj + timedelta(days=1) - timedelta(seconds=1))
                        except ValueError:
                            pass
        
        # Try parsing as a specific date with dateutil
        try:
            parsed_date = parse_date(date_expr, fuzzy=True)
            # Set to start of day
            parsed_date = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
            # Return the full day range
            return (parsed_date, parsed_date + timedelta(days=1) - timedelta(seconds=1))
        except:
            logger.warning(f"Failed to parse date expression: '{date_expr}'")
            return None
            
    except Exception as e:
        logger.error(f"Error parsing date expression '{date_expr}': {e}")
        return None

def keyword_extract(query: str) -> List[str]:
    """
    Extract keywords from the query.
    
    Args:
        query: The user's search query
        
    Returns:
        List of extracted keywords
    """
    # Remove stopwords and punctuation
    if not nlp:
        # Fallback to simple splitting
        return [word.lower() for word in query.split() if len(word) > 3]
    
    doc = nlp(query)
    keywords = []
    
    for token in doc:
        # Keep tokens that are not stopwords, punctuation, or very short
        if not token.is_stop and not token.is_punct and len(token.text) > 3:
            keywords.append(token.text.lower())
    
    return keywords

def calculate_date_relevance(entry_date: datetime, target_date: Tuple[datetime, datetime]) -> float:
    """
    Calculate relevance score based on how close an entry date is to a target date range.
    
    Args:
        entry_date: Date of the journal entry
        target_date: Tuple of (start_date, end_date) to compare against
        
    Returns:
        Relevance score between 0 and 1
    """
    start_date, end_date = target_date
    
    # If within the exact range, maximum relevance
    if start_date <= entry_date <= end_date:
        return 1.0
    
    # Calculate days difference to the closest boundary
    if entry_date < start_date:
        days_diff = (start_date - entry_date).days
    else:  # entry_date > end_date
        days_diff = (entry_date - end_date).days
    
    # Score decreases as days difference increases
    # Use an exponential decay function
    relevance = max(0.0, min(1.0, np.exp(-0.1 * days_diff)))
    
    return relevance

def calculate_relevance_score(query: str, text: str) -> float:
    """
    Calculate a relevance score between a query and text.
    
    Args:
        query: The search query
        text: The text to score against the query
        
    Returns:
        A relevance score between 0 and 1
    """
    try:
        # Simple implementation - count keyword matches
        query_words = set(word.lower() for word in query.split() if len(word) > 3)
        if not query_words:
            return 0.5  # Default medium score if no meaningful words
            
        text_lower = text.lower()
        
        # Count matches
        matches = sum(1 for word in query_words if word in text_lower)
        
        if len(query_words) > 0:
            # Normalize to 0-1 range
            basic_score = matches / len(query_words)
            
            # Apply sigmoid to make the scoring more reasonable
            # (avoid too many 0s and 1s by making the curve more gradual)
            import math
            sigmoid = lambda x: 1 / (1 + math.exp(-10 * (x - 0.5)))
            
            # Map 0->0.1 and 1->0.9 to still allow for differences at extremes
            return 0.1 + sigmoid(basic_score) * 0.8
        else:
            return 0.5  # Default medium score
    except Exception as e:
        logger.error(f"Error calculating relevance score: {e}")
        return 0.5  # Default medium score on error

async def search_entries_advanced(
    query: str,
    limit: int = 5,
    min_score: float = 0.5,
    expand: bool = True
) -> List[Dict[str, Any]]:
    """
    Advanced search for journal entries with query expansion, entity recognition,
    query type detection, and hybrid search.
    
    Args:
        query: User's search query
        limit: Maximum number of results to return
        min_score: Minimum relevance score threshold
        expand: Whether to expand the query with related terms
        
    Returns:
        List of dictionaries containing relevant entries and scores
    """
    try:
        logger.info(f"Advanced search for query: '{query}'")
        
        # Step 1: Detect query type
        query_type = detect_query_type(query)
        logger.info(f"Detected query type: {query_type}")
        
        # Step 2: Extract entities
        entities = extract_entities(query)
        logger.info(f"Extracted entities: {entities}")
        
        # Step 3: Expand query if enabled
        if expand:
            expanded_query = await expand_query(query)
        else:
            expanded_query = query
        
        # Step 4: Perform semantic search
        semantic_results = await search_similar_entries(
            query=expanded_query,
            limit=limit * 2,  # Get more results initially for reranking
            min_score=min_score
        )
        
        # Step 5: Extract keywords for keyword search
        keywords = keyword_extract(query)
        logger.info(f"Extracted keywords: {keywords}")
        
        # Step 6: Perform keyword search
        keyword_results = await keyword_search(keywords=keywords, limit=limit * 2)
        
        # Step 7: Combine and deduplicate results
        combined_results = {}
        
        # Process semantic results
        for entry in semantic_results:
            entry_id = entry["id"]
            combined_results[entry_id] = {
                "id": entry_id,
                "title": entry["title"],
                "content": entry["content"],
                "date": entry["date"],
                "semantic_score": entry["score"],
                "keyword_score": 0.0,
                "final_score": entry["score"]  # Initial score
            }
        
        # Process keyword results
        for entry in keyword_results:
            entry_id = entry["id"]
            if entry_id in combined_results:
                # Update existing entry
                combined_results[entry_id]["keyword_score"] = entry["score"]
                # Combine scores (weighted average)
                semantic_weight = 0.7
                keyword_weight = 0.3
                combined_results[entry_id]["final_score"] = (
                    semantic_weight * combined_results[entry_id]["semantic_score"] +
                    keyword_weight * entry["score"]
                )
            else:
                # Add new entry
                combined_results[entry_id] = {
                    "id": entry_id,
                    "title": entry["title"],
                    "content": entry["content"],
                    "date": entry["date"],
                    "semantic_score": 0.0,
                    "keyword_score": entry["score"],
                    "final_score": entry["score"] * 0.5  # Lower weight for keyword-only matches
                }
        
        # Step 8: Date-specific refinement
        if query_type == 'date' and entities['dates']:
            for date_entity in entities['dates']:
                date_range = parse_date_expression(date_entity)
                if date_range:
                    logger.info(f"Parsed date range: {date_range}")
                    # Adjust scores based on date relevance
                    for entry_id, entry in combined_results.items():
                        entry_date = entry["date"]
                        date_relevance = calculate_date_relevance(entry_date, date_range)
                        # Boost score for date-relevant entries
                        entry["final_score"] = 0.3 * entry["final_score"] + 0.7 * date_relevance
        
        # Step 9: Sort by final score
        sorted_results = sorted(
            combined_results.values(), 
            key=lambda x: x["final_score"], 
            reverse=True
        )
        
        # Step 10: Filter by minimum score and return top results
        filtered_results = [
            {
                "id": entry["id"],
                "title": entry["title"],
                "content": entry["content"],
                "date": entry["date"],
                "score": entry["final_score"]
            }
            for entry in sorted_results
            if entry["final_score"] >= min_score
        ]
        
        logger.info(f"Found {len(filtered_results)} relevant entries")
        
        return filtered_results[:limit]
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        # Fall back to basic search
        logger.info("Falling back to basic search")
        return await search_similar_entries(query=query, limit=limit, min_score=min_score)

def summarize_entries(entries: List[Dict[str, Any]], query: str) -> str:
    """
    Summarize a collection of journal entries to create a focused context.
    
    Args:
        entries: List of journal entries to summarize
        query: The original user query to focus the summary
        
    Returns:
        Summarized text that focuses on information relevant to the query
    """
    try:
        if not entries:
            return ""
            
        # Format entries for summarization
        entries_text = ""
        for i, entry in enumerate(entries):
            date_str = entry["date"].strftime("%Y-%m-%d") if entry["date"] else "Unknown date"
            entries_text += f"Entry {i+1} ({date_str}):\nTitle: {entry['title']}\n{entry['content']}\n\n"
        
        # Get prompt for summarization
        prompt = PROMPT_TEMPLATES.get("ENTRIES_SUMMARIZATION", "")
        
        # Add the query to help focus the summary
        prompt += f"\n\nFocus the summary on information relevant to this question: {query}"
        
        # Generate summary
        summary = generate_openai_completion(
            prompt=prompt,
            user_content=entries_text
        )
        
        if not summary:
            # Fallback to concatenating entries with truncation
            full_text = ""
            for entry in entries:
                date_str = entry["date"].strftime("%Y-%m-%d") if entry["date"] else "Unknown date"
                content = entry["content"]
                if len(content) > 500:
                    content = content[:497] + "..."
                full_text += f"[{date_str}] {content}\n\n"
            return full_text
        
        return summary
    except Exception as e:
        logger.error(f"Error summarizing entries: {e}")
        # Fallback to concatenating entries with truncation
        full_text = ""
        for entry in entries:
            date_str = entry["date"].strftime("%Y-%m-%d") if entry["date"] else "Unknown date"
            content = entry["content"]
            if len(content) > 500:
                content = content[:497] + "..."
            full_text += f"[{date_str}] {content}\n\n"
        return full_text

async def get_relevant_entries_advanced(user_id: int, query: str, max_entries: int = 10) -> List[Dict[str, Any]]:
    logger.info(f"[AdvancedRetrieval] Starting advanced retrieval for user {user_id} with query: '{query}'")
    
    try:
        # Detect query type
        query_type = detect_query_type(query)
        logger.info(f"[AdvancedRetrieval] Detected query type: {query_type}")
        
        # Extract entities
        entities = extract_entities(query)
        # Format entity string properly based on dictionary structure
        entity_parts = []
        for entity_type, entity_list in entities.items():
            if entity_list:
                entity_parts.append(f"{entity_type}: {', '.join(entity_list)}")
        entity_str = " | ".join(entity_parts) if entity_parts else "None"
        logger.info(f"[AdvancedRetrieval] Extracted entities: {entity_str}")
        
        # Expand query for better semantic search
        expanded_query = await expand_query(query)
        logger.info(f"[AdvancedRetrieval] Expanded query: '{expanded_query}'")
        
        # Get entries using different methods
        entries = []
        relevance_boosted_entries = {}  # To keep track of entries that have boosted relevance

        # Priority 1: Date filtering if it's a date query
        date_entries = []
        if query_type == 'date' and entities.get('dates'):
            logger.info(f"[AdvancedRetrieval] Processing as date query with entities: {entities['dates']}")
            for date_str in entities['dates']:
                logger.info(f"[AdvancedRetrieval] Attempting date filtering with date: {date_str}")
                filtered_entries = await filter_entries_by_date(user_id, date_str)
                
                if filtered_entries:
                    # Boost score for exact date matches
                    for entry in filtered_entries:
                        entry_id = entry['id']
                        if entry_id not in relevance_boosted_entries:
                            entry['similarity'] = 0.95  # Very high score for exact date matches
                            relevance_boosted_entries[entry_id] = entry
                    date_entries.extend(filtered_entries)
                    logger.info(f"[AdvancedRetrieval] Found {len(filtered_entries)} entries for date: {date_str}")
                else:
                    logger.info(f"[AdvancedRetrieval] No entries found for date: {date_str}")
            
            if date_entries:
                entries.extend(date_entries)
                logger.info(f"[AdvancedRetrieval] Found {len(date_entries)} total entries via date filtering")
        
        # Method 2: Semantic search - always try this regardless of query type
        min_similarity = 0.3 if query_type == 'date' else 0.5  # Lower threshold for date queries
        limit_multiplier = 3 if len(entries) < max_entries else 1  # Get more semantic results if date filtering found few entries
        
        semantic_entries = await search_similar_entries(user_id, expanded_query, limit=max_entries*limit_multiplier, min_score=min_similarity)
        if semantic_entries:
            # Remove duplicates already found by date filtering
            existing_ids = set(e['id'] for e in entries)
            unique_semantic_entries = [e for e in semantic_entries if e['id'] not in existing_ids]
            
            if unique_semantic_entries:
                entries.extend(unique_semantic_entries)
                logger.info(f"[AdvancedRetrieval] Found {len(unique_semantic_entries)} entries via semantic search")
                for i, entry in enumerate(unique_semantic_entries[:3]):  # Log first 3 entries
                    logger.info(f"[AdvancedRetrieval] Semantic result #{i+1}: ID={entry['id']}, Date={entry.get('date')}, Score={entry.get('similarity', 'N/A')}")
        
        # Method 3: Keyword search if semantic search didn't find enough
        if len(entries) < max_entries:
            # Extract keywords for search
            keywords = []
            if query_type == 'date' and entities.get('dates'):
                # For date queries, add month names as keywords
                month_names = ["january", "february", "march", "april", "may", "june", "july", 
                              "august", "september", "october", "november", "december"]
                for date_str in entities['dates']:
                    for month in month_names:
                        if month in date_str.lower():
                            keywords.append(month)
            
            # Add general keywords from the query
            if not keywords:  # Only if we don't have date-specific keywords
                keywords = keyword_extract(query)
            
            if keywords:
                logger.info(f"[AdvancedRetrieval] Performing keyword search with: {keywords}")
                keyword_entries = await keyword_search(user_id, query, limit=max_entries)
                if keyword_entries:
                    # Remove duplicates
                    existing_ids = set(e['id'] for e in entries)
                    unique_keyword_entries = [e for e in keyword_entries if e['id'] not in existing_ids]
                    
                    if unique_keyword_entries:
                        entries.extend(unique_keyword_entries)
                        logger.info(f"[AdvancedRetrieval] Found {len(unique_keyword_entries)} unique entries via keyword search")
                        for i, entry in enumerate(unique_keyword_entries[:3]):  # Log first 3 entries
                            logger.info(f"[AdvancedRetrieval] Keyword result #{i+1}: ID={entry['id']}, Date={entry.get('date')}")
        
        # Sort by relevance and limit results
        if entries:
            # Apply additional relevance scoring based on query type
            for entry in entries:
                entry_id = entry['id']
                # Skip entries that already have boosted relevance
                if entry_id in relevance_boosted_entries:
                    continue
                
                # Make sure all entries have a similarity score
                if 'similarity' not in entry:
                    entry['similarity'] = calculate_relevance_score(query, entry.get('content', ''))
                
                # Boost score for entries matching query type
                if query_type == 'date' and entities.get('dates'):
                    # Check if the entry date is close to any of the queried dates
                    entry_date = entry.get('date')
                    if entry_date:
                        for date_str in entities['dates']:
                            date_range = parse_date_expression(date_str)
                            if date_range and isinstance(entry_date, datetime):
                                date_relevance = calculate_date_relevance(entry_date, date_range)
                                # Blend the scores, emphasizing date relevance
                                entry['similarity'] = 0.3 * entry['similarity'] + 0.7 * date_relevance
            
            # Sort by relevance score
            entries = sorted(entries, key=lambda x: x.get('similarity', 0), reverse=True)
            
            # Limit to max_entries
            entries = entries[:max_entries]
            
            logger.info(f"[AdvancedRetrieval] Final result: {len(entries)} entries returned after sorting and limiting")
            for i, entry in enumerate(entries[:5]):  # Log top 5 entries
                logger.info(f"[AdvancedRetrieval] Final result #{i+1}: ID={entry['id']}, Date={entry.get('date')}, Score={entry.get('similarity', 'N/A')}")
        else:
            logger.warning(f"[AdvancedRetrieval] No entries found for user {user_id} with query: '{query}'")
        
        return entries
    
    except Exception as e:
        logger.error(f"[AdvancedRetrieval] Error in advanced retrieval: {str(e)}")
        logger.exception(e)
        return [] 