from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from app.routes import auth, journal, assistant
from app.config import settings

app = FastAPI(title="JournalMind")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(journal.router, prefix="/journal", tags=["journal"])
app.include_router(assistant.router, prefix="/assistant", tags=["assistant"])

# Configure TortoiseORM
register_tortoise(
    app,
    db_url=settings.DATABASE_URL,
    modules={"models": ["app.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

@app.on_event("startup")
async def startup_event():
    print("JournalMind API is starting up...")