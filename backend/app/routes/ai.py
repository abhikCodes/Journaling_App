from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import crud, schemas, auth
from ..database import get_db
from ..utils.rag import get_relevant_chunks, generate_response

router = APIRouter()

@router.post("/query")
async def ai_query(
    query: schemas.AIQuery,
    db: Session = Depends(get_db),
    current_user: str = Depends(auth.get_current_user)
):
    user = crud.get_user_by_username(db, current_user)
    recent_entries = crud.get_journal_entries(db, user.id, limit=5)
    entry_texts = [entry.text for entry in recent_entries]
    context = "\n".join(entry_texts)
    
    chunks = await get_relevant_chunks(query.query)
    psychology_context = "\n".join([chunk["text"] for chunk in chunks])
    
    full_context = f"Journal Entries:\n{context}\n\nPsychology Knowledge:\n{psychology_context}"
    
    response = await generate_response(query.query, full_context)
    return {"response": response}