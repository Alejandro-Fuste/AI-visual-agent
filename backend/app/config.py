from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "visual-agent-backend")
    ENV: str = os.getenv("ENV", "dev")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")  # comma-separated
    
    # LLM API Configuration
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://127.0.0.1:5000")
    LLM_API_TIMEOUT: int = int(os.getenv("LLM_API_TIMEOUT", "120"))  # 2 minutes for LLM processing
    
    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8080"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

settings = Settings()
