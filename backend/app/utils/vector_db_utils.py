from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import settings
import os
import logging
from typing import List, Dict, Any, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

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

async def create_embedding(text: str) -> List[float]:
    """
    Create an embedding vector from text
    """
    return model.encode(text).tolist()

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
        # Create embedding for the content
        embedding = await create_embedding(content)
        
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

async def search_similar_entries(
    user_id: int,
    query: str, 
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for journal entries similar to the query
    """
    try:
        # Create embedding for the query
        query_embedding = await create_embedding(query)
        
        # Search in Qdrant
        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit
        )
        
        # Format results
        results = []
        for result in search_result:
            results.append({
                "id": result.id,
                "content": result.payload.get("content"),
                "date": result.payload.get("date"),
                "tags": result.payload.get("tags"),
                "score": result.score
            })
        
        return results
    except Exception as e:
        logger.error(f"Failed to search journal entries: {str(e)}")
        return [] 