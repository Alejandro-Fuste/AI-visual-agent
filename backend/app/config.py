from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = BASE_DIR / "runtime"


class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "visual-agent-backend")
    ENV: str = os.getenv("ENV", "dev")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    HF_OMNIPARSER_URL: str = os.getenv("HF_OMNIPARSER_URL", "")
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", os.getenv("QWEN_API_KEY", ""))
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", os.getenv("QWEN_API_BASE", "https://api.openai.com/v1"))
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", os.getenv("QWEN_MODEL", "gpt-4o-mini"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", os.getenv("QWEN_TEMPERATURE", "0.0")))

    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "3"))
    AGENT_RUNS_DIR: Path = Path(os.getenv("AGENT_RUNS_DIR", str((RUNTIME_DIR / "runs").resolve())))
    AGENT_ENABLE_OVERLAY: bool = os.getenv("AGENT_ENABLE_OVERLAY", "true").lower() == "true"
    AGENT_DRY_RUN: bool = os.getenv("AGENT_DRY_RUN", "false").lower() == "true"
    AGENT_ACTION_PAUSE: float = float(os.getenv("AGENT_ACTION_PAUSE", "0.35"))


settings = Settings()
settings.AGENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
