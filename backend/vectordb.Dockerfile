FROM qdrant/qdrant

EXPOSE 6333
EXPOSE 6334

# Default Qdrant configuration with persistent storage
ENV QDRANT_STORAGE_PATH=/qdrant/storage

# Create volume for persistence
VOLUME ["/qdrant/storage"] 