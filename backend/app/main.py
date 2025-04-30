# main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security.api_key import APIKeyHeader
from tortoise.contrib.fastapi import register_tortoise
from app.routes import auth, journal, assistant
from app.config import settings
from app.services.assistant_service import init_assistant

app = FastAPI(title="JournalMind")

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

# Configure Tortoise ORM
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
    await init_assistant()
