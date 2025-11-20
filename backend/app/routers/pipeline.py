from __future__ import annotations

from datetime import datetime
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Body

from app.config import settings
from app.pipeline.runner import run_full_pipeline
from app.schemas import LogEntry, RepromptRequest, RepromptResponse, RunResponse, StatusResponse

router = APIRouter(prefix="/api", tags=["pipeline"])

RUNS: dict[str, dict] = {}


def _slugify_prompt(prompt: str, max_length: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")
    if not slug:
        slug = "run"
    return slug[:max_length]


def _build_run_directory(prompt: str) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    slug = _slugify_prompt(prompt)
    base_name = f"{timestamp}-{slug}"
    run_dir = (settings.AGENT_RUNS_DIR / base_name).resolve()
    counter = 1
    while run_dir.exists():
        run_dir = (settings.AGENT_RUNS_DIR / f"{base_name}-{counter}").resolve()
        counter += 1
    return run_dir


@router.post("/run", response_model=RunResponse)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...),
):
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    run_id = str(uuid4())
    run_dir = _build_run_directory(prompt)
    screenshots_dir = run_dir / "screenshots"
    logs_dir = run_dir / "logs"
    pipeline_dir = run_dir / "pipeline"
    for path in [run_dir, screenshots_dir, logs_dir, pipeline_dir]:
        path.mkdir(parents=True, exist_ok=True)

    RUNS[run_id] = {
        "status": "running",
        "logs": [LogEntry(stage="queued", message="Run submitted", timestamp=datetime.utcnow())],
        "result": None,
        "prompt": prompt,
        "clarifications": [],
        "pending_question": None,
        "run_dir": str(run_dir),
    }

    background_tasks.add_task(
        real_pipeline,
        run_id,
        prompt,
        str(run_dir),
        RUNS[run_id]["clarifications"].copy(),
    )
    return RunResponse(
        run_id=run_id,
        status="running",
        logs=RUNS[run_id]["logs"],
        result=None,
        pending_question=None,
    )


def real_pipeline(
    run_id: str,
    prompt: str,
    run_dir: str | Path | None = None,
    clarifications: list[str] | None = None,
):
    result = run_full_pipeline(run_id, prompt, clarifications=clarifications, run_dir=run_dir)
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
        run.get("run_dir"),
        run["clarifications"].copy(),
    )

    return RepromptResponse(acknowledged=True, message="User input received")
