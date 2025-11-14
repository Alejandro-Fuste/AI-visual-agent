from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any
from datetime import datetime


# ---- Shared ----
class LogEntry(BaseModel):
    stage: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---- /run ----
class RunRequest(BaseModel):
    prompt: str
    file_path: Optional[str] = None
    allow_reprompt: bool = True
    options: Optional[dict] = None


class RunResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "success", "error"]
    logs: List[LogEntry] = []
    result: Optional[Any] = None
    error: Optional[str] = None


# ---- /status/{run_id} ----
class StatusResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "success", "error"]
    logs: List[LogEntry]
    result: Optional[Any] = None  # Include the result in status response


# ---- /reprompt ----
class RepromptRequest(BaseModel):
    run_id: str
    message: str


class RepromptResponse(BaseModel):
    acknowledged: bool
    message: Optional[str] = None
