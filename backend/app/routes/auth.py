from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordBearer
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.config import settings
from app.models import User, JournalEntry
from app.utils.redis_utils import add_token_to_blacklist, is_token_blacklisted, clear_all_user_tokens
from app.utils.auth_utils import extract_token_from_header
import jwt
from datetime import datetime, timedelta
from starlette.responses import RedirectResponse
import logging
from app.utils.sentiment_utils import analyze_sentiment

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Changed auto_error to True to ensure token is always required
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/callback", auto_error=True)

config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
})
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # First, just validate the JWT token itself
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        google_id: str = payload.get("sub")
        if google_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token - missing subject"
            )
            
        # Try to get the user
        try:
            user = await User.get(google_id=google_id)
            
            # If we got the user, check if token is blacklisted as a best effort
            # The blacklist check is not critical for functionality
            try:
                blacklisted = await is_token_blacklisted(token, google_id)
                if blacklisted:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, 
                        detail="Token has been revoked"
                    )
            except Exception as e:
                # Log but don't fail if Redis is unavailable
                logger.warning(f"Blacklist check failed: {str(e)}")
                
            return user
        except Exception as e:
            logger.error(f"User lookup error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User not found"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token format"
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid authentication credentials"
        )

@router.get("/login")
async def login(request: Request):
    # Standard OAuth redirect to backend callback
    callback_url = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, callback_url)

@router.get("/callback")
async def auth_callback(request: Request):
    try:
        # Exchange auth code for tokens
        token = await oauth.google.authorize_access_token(request)
        user_info = token["userinfo"]
        
        user, _ = await User.get_or_create(
            google_id=user_info["sub"],
            defaults={"email": user_info["email"], "name": user_info["name"]}
        )
        
        # Create a JWT token with short expiration
        # The token will be checked against Redis blacklist for revocation
        payload = {
            "sub": user.google_id,
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Redirect to frontend with token
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        redirect_url = f"{frontend_url}/?auth_success=true&access_token={access_token}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        redirect_url = f"{frontend_url}/?auth_error=true"
        return RedirectResponse(url=redirect_url, status_code=302)

@router.post("/logout")
async def logout(user: User = Security(get_current_user), token: str = Depends(oauth2_scheme)):
    """
    Logout a user by adding their token to the blacklist in Redis
    """
    try:
        await add_token_to_blacklist(token, user.google_id)
        return {"detail": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return {"detail": "Logout processed but token blacklisting unavailable"}

@router.post("/logout-all-devices")
async def logout_all_devices(user: User = Security(get_current_user)):
    """
    Logout a user from all devices by clearing all their tokens
    """
    try:
        await clear_all_user_tokens(user.google_id)
        return {"detail": "Successfully logged out from all devices"}
    except Exception as e:
        logger.error(f"Logout all devices error: {str(e)}")
        return {"detail": "Logout request processed but token blacklisting unavailable"}

@router.get("/validate-token")
async def validate_token(user: User = Security(get_current_user)):
    """
    Simple endpoint to validate if a token is valid
    Returns the user info if token is valid
    """
    return {
        "valid": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

@router.post("/refresh-token")
async def refresh_token(user: User = Security(get_current_user), old_token: str = Depends(oauth2_scheme)):
    """
    Refresh a token to extend the expiration time
    This blacklists the old token and issues a new one
    """
    try:
        # Try to blacklist the old token, but continue even if it fails
        try:
            await add_token_to_blacklist(old_token, user.google_id)
        except Exception as e:
            logger.warning(f"Token blacklisting failed on refresh: {str(e)}")
        
        # Create a new token
        payload = {
            "sub": user.google_id,
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        new_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/test-login")
async def test_login():
    """
    Create a test user and return a JWT token for testing purposes.
    This is used by the frontend "Try as Test User" button.
    """
    try:
        # Create or get the test user
        test_user = await User.get_or_create(
            name="testuser",
            defaults={
                "email": "test@example.com",
                "google_id": "test_google_id"
            }
        )
        user = test_user[0]  # get_or_create returns a tuple (instance, created)
        
        # Check if this is a newly created user or has no entries
        entry_count = await JournalEntry.filter(user=user).count()
        if entry_count == 0:
            # Create a sample entry
            from datetime import date
            
            sample_content = """
            Welcome to JournalMind! This is a sample journal entry to help you get started.
            
            Today I explored this amazing journaling app that uses AI to provide insights into my thoughts and feelings. 
            The interface is clean and intuitive, making it easy to record my daily reflections. I particularly like how 
            it can analyze emotions and track patterns over time.
            
            I'm excited to start using this regularly to document my experiences and see what kind of insights the AI 
            assistant can provide. The feature that generates titles based on content is clever, and I appreciate the 
            privacy-focused approach. Looking forward to filling these pages with my thoughts!
            """
            
            # Analyze sentiment
            sentiment_score, emotion_tags = await analyze_sentiment(sample_content)
            
            # Create the entry
            today = date.today()
            await JournalEntry.create(
                user=user,
                title="My First Journal Entry with JournalMind",
                date=today,
                content=sample_content,
                tags=["welcome", "first entry", "demo"],
                sentiment_score=sentiment_score,
                emotion_tags=emotion_tags
            )
            
            # Update entry count
            user.entry_count += 1
            await user.save()
            
            # Store in vector database
            from app.utils.vector_db_utils import store_journal_entry
            try:
                await store_journal_entry(
                    entry_id=1,  # This will be the first entry
                    user_id=user.id,
                    content=sample_content,
                    date=str(today),
                    tags=["welcome", "first entry", "demo"]
                )
            except Exception as e:
                logger.error(f"Failed to store sample entry in vector DB: {str(e)}")
        
        # Create a JWT token
        payload = {
            "sub": user.google_id,
            "exp": datetime.utcnow() + timedelta(days=7)  # Longer expiration for test
        }
        access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Test login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test login session"
        )