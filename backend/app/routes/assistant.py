from fastapi import APIRouter, Depends, HTTPException, Body
from app.services.assistant_service import handle_assistant_message
from app.routes.auth import get_current_user
from app.models import User

router = APIRouter()

@router.post("/message")
async def send_message(message: str = Body(..., embed=True), user: User = Depends(get_current_user)):
    response = await handle_assistant_message(user, message)
    return {"response": response}