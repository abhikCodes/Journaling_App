import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgres://user:password@localhost:5432/journalmind")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    # URL of the frontend application for OAuth callback
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3001")
    PRODUCTION_ENV = os.getenv("PRODUCTION_ENV", "false").lower() == "true"
    # Redis configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    # Token blacklist TTL (in seconds) - 30 days
    TOKEN_BLACKLIST_TTL = 60 * 60 * 24 * 30

settings = Settings()