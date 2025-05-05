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
        is_new_user = test_user[1]  # Returns True if user was created
        
        # Check if this is a newly created user or has no entries
        entry_count = await JournalEntry.filter(user=user).count()
        
        # Create a JWT token
        payload = {
            "sub": user.google_id,
            "exp": datetime.utcnow() + timedelta(days=7)  # Longer expiration for test
        }
        access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # If no entries, we'll tell the frontend to use the CSV data
        # But still return a valid token immediately
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "setup_needed": entry_count == 0,
            "is_new_user": is_new_user
        }
    except Exception as e:
        logger.error(f"Test login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test login session"
        )

@router.post("/setup-test-user")
async def setup_test_user(user: User = Depends(get_current_user)):
    """
    Set up predefined journal entries for a test user from the CSV file.
    """
    try:
        # Check if this is the test user
        if user.email != "test@example.com" and "test" not in user.name.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only for test users"
            )
            
        # Check if user already has entries
        entry_count = await JournalEntry.filter(user=user).count()
        if entry_count > 0:
            return {"message": "User already has entries", "entry_count": entry_count}
        
        # Import the test_genesis_upload function
        from app.routes.journal import test_genesis_upload
        
        # Call the test_genesis_upload function with 'all' mode to process all entries
        try:
            result = await test_genesis_upload(mode="all")
            return {
                "message": "Successfully set up test user with entries from CSV file",
                "created_count": result.get("processed", 0),
                "total": result.get("total", 0)
            }
        except Exception as e:
            logger.error(f"Error in test_genesis_upload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load entries from CSV: {str(e)}"
            )
    except Exception as e:
        logger.error(f"Error setting up test user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set up test user: {str(e)}"
        )