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

    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_API_BASE: str = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen2.5-vl-7b-instruct")
    QWEN_TEMPERATURE: float = float(os.getenv("QWEN_TEMPERATURE", "0.15"))

    AGENT_MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "3"))
    AGENT_RUNS_DIR: Path = Path(os.getenv("AGENT_RUNS_DIR", str((RUNTIME_DIR / "runs").resolve())))
    AGENT_ENABLE_OVERLAY: bool = os.getenv("AGENT_ENABLE_OVERLAY", "true").lower() == "true"
    AGENT_DRY_RUN: bool = os.getenv("AGENT_DRY_RUN", "false").lower() == "true"
    AGENT_ACTION_PAUSE: float = float(os.getenv("AGENT_ACTION_PAUSE", "0.35"))


settings = Settings()
settings.AGENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
