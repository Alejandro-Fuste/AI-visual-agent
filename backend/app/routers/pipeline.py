from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from app.schemas import RunResponse, StatusResponse, RepromptRequest, RepromptResponse, LogEntry
from app.pipeline.runner import run_full_pipeline
from uuid import uuid4
from datetime import datetime
import os, json
from pathlib import Path

router = APIRouter(prefix="/api", tags=["pipeline"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Temporary in-memory storage (replace later with DB or log files)
RUNS = {}

@router.post("/run", response_model=RunResponse)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    file: UploadFile | None = File(None)
):
    """Accepts prompt + optional file upload, starts pipeline."""
    run_id = str(uuid4())
    file_path = None

    if file:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

    RUNS[run_id] = {
        "status": "running",
        "logs": [LogEntry(stage="init", message="Pipeline started", timestamp=datetime.utcnow())],
        "result": None,
    }

    # run the pipeline asynchronously
    background_tasks.add_task(real_pipeline, run_id, prompt, file_path)
    return RunResponse(run_id=run_id, status="running", logs=RUNS[run_id]["logs"])

def real_pipeline(run_id: str, prompt: str, file_path: str | None = None):
    result = run_full_pipeline(prompt, file_path)
    RUNS[run_id]["status"] = result["status"]
    RUNS[run_id]["logs"].extend(result["logs"])
    RUNS[run_id]["result"] = result["result"]


def fake_pipeline(run_id: str):
    import time
    stages = ["YOLO", "BLIP", "LLM"]
    for stage in stages:
        time.sleep(1)
        RUNS[run_id]["logs"].append(LogEntry(stage=stage, message=f"{stage} completed"))
    RUNS[run_id]["status"] = "success"
    RUNS[run_id]["result"] = {"summary": "Demo pipeline finished successfully"}


@router.get("/status/{run_id}", response_model=StatusResponse)
async def get_status(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return StatusResponse(run_id=run_id, status=run["status"], logs=run["logs"])


@router.post("/reprompt", response_model=RepromptResponse)
async def handle_reprompt(payload: RepromptRequest):
    """Called when the LLM needs additional user input."""
    log_entry = LogEntry(stage="reprompt", message=payload.message)
    run = RUNS.get(payload.run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found")

    # Add to in-memory logs
    run["logs"].append(log_entry)

    # Persist to a JSON log file
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{payload.run_id}.json"

    try:
        # Load existing log file if it exists
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"run_id": payload.run_id, "logs": []}

        # Merge existing logs with current in-memory run logs
        all_logs = data.get("logs", [])
        all_logs.extend(
            {"stage": log.stage, "message": log.message}
            for log in run["logs"]
            if {"stage": log.stage, "message": log.message} not in all_logs
        )

        # Write updated logs back to file
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"run_id": payload.run_id, "logs": all_logs}, f, indent=4)

    except Exception as e:
        print(f"⚠️ Error writing re-prompt log: {e}")

    return RepromptResponse(acknowledged=True, message="User input received and logged")
