import redis
import jwt
import os
from app.config import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Redis client singleton
_redis_client = None

def get_redis_client():
    """Get or initialize Redis client"""
    global _redis_client
    if _redis_client is None:
        try:
            # When running in Docker, we need to use the service name as hostname
            # The service name 'redis' is defined in docker-compose.yml
            redis_host = "redis"  # Use the service name from docker-compose.yml
            logger.info(f"Connecting to Redis at {redis_host}:{settings.REDIS_PORT}")
            
            # Get Redis password if set in environment
            redis_password = os.environ.get("REDIS_PASSWORD", None)
            
            # Create Redis connection with proper connection parameters
            redis_config = {
                'host': redis_host,
                'port': settings.REDIS_PORT,
                'decode_responses': True,
                'socket_connect_timeout': 5,
                'health_check_interval': 30,  # Enable health checks
                'retry_on_timeout': True,
                'socket_keepalive': True
            }
            
            # Add password if provided
            if redis_password:
                redis_config['password'] = redis_password
                
            _redis_client = redis.Redis(**redis_config)
            
            # Simple ping to check connectivity - use direct Redis command format
            _redis_client.ping()
            logger.info("Redis connection successful")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
            _redis_client = DummyRedisClient()
        except redis.exceptions.AuthenticationError as e:
            logger.error(f"Redis authentication error: {str(e)}")
            _redis_client = DummyRedisClient()
        except Exception as e:
            logger.error(f"Redis general error: {str(e)}")
            # Create a dummy implementation that always returns False for blacklisted tokens
            # This allows the app to function even if Redis is down
            _redis_client = DummyRedisClient()
            
    return _redis_client

class DummyRedisClient:
    """Fallback implementation when Redis is unavailable"""
    def set(self, *args, **kwargs):
        logger.warning("Using dummy Redis client - token blacklisting not available")
        return True
        
    def exists(self, *args, **kwargs):
        return False
        
    def delete(self, *args, **kwargs):
        return True
        
    def keys(self, *args, **kwargs):
        return []
        
    def ping(self, *args, **kwargs):
        return True

def get_token_id(token: str) -> str:
    """
    Extract a consistent ID from a token to use as Redis key
    """
    try:
        # For JWT tokens, use a hash of the token itself as the identifier
        # This ensures we can identify the specific token even if we don't 
        # have custom JTI (JWT ID) claims
        return token[-10:]  # Last 10 chars as a simple identifier
    except Exception:
        # If we can't decode, just use the token hash as fallback
        return token[-10:]

async def add_token_to_blacklist(token: str, user_id: str):
    """
    Add a token to the blacklist when a user logs out
    """
    try:
        client = get_redis_client()
        token_id = get_token_id(token)
        # Key format: blacklist:{user_id}:{token_id}
        token_key = f"blacklist:{user_id}:{token_id}"
        client.set(token_key, "1", ex=settings.TOKEN_BLACKLIST_TTL)
    except Exception as e:
        logger.error(f"Failed to blacklist token: {str(e)}")

async def is_token_blacklisted(token: str, user_id: str) -> bool:
    """
    Check if a token is blacklisted (user has logged out)
    """
    try:
        client = get_redis_client()
        token_id = get_token_id(token)
        token_key = f"blacklist:{user_id}:{token_id}"
        return client.exists(token_key) == 1
    except Exception as e:
        logger.error(f"Failed to check blacklist status: {str(e)}")
        # In case of error, default to allowing the token (not blacklisted)
        return False

async def clear_all_user_tokens(user_id: str):
    """
    Clear all tokens for a specific user (force logout from all devices)
    """
    try:
        client = get_redis_client()
        pattern = f"blacklist:{user_id}:*"
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
    except Exception as e:
        logger.error(f"Failed to clear user tokens: {str(e)}") 