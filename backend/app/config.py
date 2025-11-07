from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "visual-agent-backend")
    ENV: str = os.getenv("ENV", "dev")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")  # comma-separated

settings = Settings()
