from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    stage: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RunRequest(BaseModel):
    prompt: str
    file_path: Optional[str] = None
    allow_reprompt: bool = True
    options: Optional[dict] = None


class RunResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "success", "error", "needs_input"]
    logs: List[LogEntry] = []
    result: Optional[Any] = None
    pending_question: Optional[str] = None
    error: Optional[str] = None


class StatusResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "success", "error", "needs_input"]
    logs: List[LogEntry]
    result: Optional[Any] = None
    pending_question: Optional[str] = None


class RepromptRequest(BaseModel):
    run_id: str
    message: str


class RepromptResponse(BaseModel):
    acknowledged: bool
    message: Optional[str] = None
