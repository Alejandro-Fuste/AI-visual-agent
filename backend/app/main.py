from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logging_config import configure_logging
from app.routers import health, pipeline
import logging

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        description="Visual Agent Backend - Connected to LLM API",
        version="1.0.0"
    )

    # CORS - Allow frontend on various ports
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(pipeline.router)
    
    # Log configuration on startup
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"🚀 {settings.APP_NAME} starting...")
        logger.info(f"📡 LLM API configured at: {settings.LLM_API_URL}")
        logger.info(f"🌐 Server running on: {settings.HOST}:{settings.PORT}")

    return app

app = create_app()
