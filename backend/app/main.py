# main.py
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security.api_key import APIKeyHeader
from tortoise.contrib.fastapi import register_tortoise
from app.routes import auth, journal, assistant, insights, analytics
from app.config import settings
# Import but not used at startup - assistant is initialized on-demand when needed
from app.services.assistant_service import init_assistant
from app.utils.vector_db_utils import init_vector_db
from fastapi.middleware.cors import CORSMiddleware
from app.utils.redis_utils import get_redis_client
from app.migrations import run_migrations
from fastapi.staticfiles import StaticFiles
import os
import logging
import time
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="JournalMind")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SessionMiddleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    same_site="lax",
)

# Define APIKeyHeader for Swagger
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# Create a custom OpenAPI schema function
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="JournalMind API",
        version="1.0.0",
        description="API for JournalMind - Your personal journaling assistant with AI-powered insights.",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"] = {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    }
    
    # Apply security to all endpoints
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Override FastAPI's openapi method
app.openapi = custom_openapi

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(journal.router, prefix="/journal", tags=["journal"])
app.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Ensure uploads directory exists
UPLOADS_DIR = "uploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# Mount static files directory for serving uploaded images
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Configure Tortoise ORM
register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["app.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

# Import and initialize our AI logger
from app.utils.ai.logger import ai_logger

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

async def initialize_redis_with_retry(max_retries=5, retry_delay=2):
    """
    Try to connect to Redis with retries
    """
    retries = 0
    while retries < max_retries:
        try:
            client = get_redis_client()
            client.ping()
            logger.info("Redis connection established")
            return True
        except Exception as e:
            retries += 1
            logger.warning(f"Redis connection attempt {retries} failed: {str(e)}")
            if retries >= max_retries:
                logger.error("Max Redis connection retries reached. Continuing without Redis.")
                return False
            time.sleep(retry_delay)

@app.on_event("startup")
async def startup_event():
    logger.info("JournalMind API is starting up...")
    
    # Run database migrations
    try:
        migration_success = await run_migrations()
        if migration_success:
            logger.info("Database migrations completed successfully")
        else:
            logger.warning("Database migrations completed with warnings")
    except Exception as e:
        logger.error(f"Database migration error: {str(e)}")
    
    # Initialize Redis connection with retries
    redis_available = await initialize_redis_with_retry()
    if not redis_available:
        logger.warning("System will operate without Redis token blacklisting")
    
    # Initialize vector database
    vectordb_available = await init_vector_db()
    if not vectordb_available:
        logger.warning("System will operate without vector database capabilities")
    
    # Don't initialize assistant on startup - it will be created on-demand
    # await init_assistant()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("JournalMind API is shutting down...")
