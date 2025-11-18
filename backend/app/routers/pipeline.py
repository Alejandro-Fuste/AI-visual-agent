from __future__ import annotations

import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.pipeline.runner import run_full_pipeline
from app.schemas import LogEntry, RepromptRequest, RepromptResponse, RunResponse, StatusResponse

router = APIRouter(prefix="/api", tags=["pipeline"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

RUNS: dict[str, dict] = {}


@router.post("/run", response_model=RunResponse)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    file: UploadFile | None = File(None),
):
    run_id = str(uuid4())
    file_path = None

    if file:
        file_path = os.path.join(UPLOAD_DIR, f"{run_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(await file.read())

    RUNS[run_id] = {
        "status": "running",
        "logs": [LogEntry(stage="queued", message="Run submitted", timestamp=datetime.utcnow())],
        "result": None,
        "prompt": prompt,
        "file_path": file_path,
        "clarifications": [],
        "pending_question": None,
    }

    background_tasks.add_task(real_pipeline, run_id, prompt, file_path, RUNS[run_id]["clarifications"].copy())
    return RunResponse(
        run_id=run_id,
        status="running",
        logs=RUNS[run_id]["logs"],
        result=None,
        pending_question=None,
    )


def real_pipeline(run_id: str, prompt: str, file_path: str | None = None, clarifications: list[str] | None = None):
    result = run_full_pipeline(run_id, prompt, file_path, clarifications=clarifications)
    run = RUNS.get(run_id)
    if not run:
        return
    run["status"] = result["status"]
    run["logs"].extend(result["logs"])
    run["result"] = result["result"]
    run["pending_question"] = result.get("pending_question")


@router.get("/status/{run_id}", response_model=StatusResponse)
async def get_status(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return StatusResponse(
        run_id=run_id,
        status=run["status"],
        logs=run["logs"],
        result=run.get("result"),
        pending_question=run.get("pending_question"),
    )


@router.post("/reprompt", response_model=RepromptResponse)
async def handle_reprompt(payload: RepromptRequest, background_tasks: BackgroundTasks):
    """Called when the LLM needs additional user input."""
    run = RUNS.get(payload.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")

    log_entry = LogEntry(stage="reprompt", message=payload.message, timestamp=datetime.utcnow())
    run["logs"].append(log_entry)
    run["clarifications"].append(payload.message)
    run["pending_question"] = None
    run["status"] = "running"

    background_tasks.add_task(
        real_pipeline,
        payload.run_id,
        run["prompt"],
        run.get("file_path"),
        run["clarifications"].copy(),
    )

    return RepromptResponse(acknowledged=True, message="User input received")
