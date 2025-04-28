from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from .. import crud, auth
from ..database import get_db
import requests
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

@router.get("/google")
async def google_login(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": "http://localhost:8000/auth/google",
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    tokens = response.json()
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="No ID token received")

    # Verify ID token
    idinfo = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}").json()
    if "error" in idinfo:
        raise HTTPException(status_code=401, detail="Invalid token")

    google_id = idinfo['sub']
    email = idinfo['email']
    name = idinfo['name']

    # Check if user exists, else create new user
    user = crud.get_user_by_google_id(db, google_id)
    if not user:
        user = crud.create_user(db, google_id, email, name)

    # Generate JWT
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    redirect_url = f"http://localhost:3000/login-success?token={access_token}"
    return RedirectResponse(url=redirect_url)