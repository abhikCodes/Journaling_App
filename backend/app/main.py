# main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security.api_key import APIKeyHeader
from tortoise.contrib.fastapi import register_tortoise
from app.routes import auth, journal, assistant, insights, analytics
from app.config import settings
from app.services.assistant_service import init_assistant
from app.utils.vector_db_utils import init_vector_db
from fastapi.middleware.cors import CORSMiddleware
from app.utils.redis_utils import get_redis_client
from app.migrations import run_migrations
import logging
import time

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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    # Generate a fresh schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Add our BearerAuth scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Bearer {token}\""
        }
    }
    # Apply globally
    for path in openapi_schema["paths"].values():
        for op in path.values():
            op.setdefault("security", []).append({"BearerAuth": []})

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

# Configure Tortoise ORM
register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["app.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

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
    
    await init_assistant()

@app.on_event("shutdown")
async def shutdown_event():
    # Close Redis connection if needed
    logger.info("JournalMind API is shutting down...")
