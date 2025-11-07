from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logging_config import configure_logging
from app.routers import health, pipeline

def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.APP_NAME)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    
    app.include_router(health.router)
    app.include_router(pipeline.router)

    return app

app = create_app()
