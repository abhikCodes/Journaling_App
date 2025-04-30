from fastapi import APIRouter, Depends
from app.schemas import AssistantRequest, AssistantMessage
from app.services.assistant_service import handle_assistant_message
from app.routes.auth import get_current_user
from app.models import User

router = APIRouter()

@router.post("/message", response_model=AssistantMessage)
async def send_message(req: AssistantRequest, user: User = Depends(get_current_user)):
    response_text = await handle_assistant_message(user, req.message)
    return AssistantMessage(message=response_text)
