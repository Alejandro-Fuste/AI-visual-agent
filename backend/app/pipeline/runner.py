from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.agent.engine import VisualAgentEngine
from app.config import settings
from app.schemas import LogEntry

LOG_DIR = (settings.AGENT_LOG_DIR.parent / "pipeline").resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)


def run_full_pipeline(
    run_id: str,
    prompt: str,
    file_path: Optional[str] = None,
    clarifications: Optional[List[str]] = None,
):
    logs: list[LogEntry] = []

    def log(stage: str, message: str) -> None:
        entry = LogEntry(stage=stage, message=message, timestamp=datetime.utcnow())
        logs.append(entry)
        print(f"[{stage}] {message}")

    log("init", f"Pipeline started for prompt: {prompt}")

    try:
        engine = VisualAgentEngine(
            run_id,
            screenshot_dir=settings.AGENT_SCREENSHOT_DIR,
            log_dir=settings.AGENT_LOG_DIR,
            max_iterations=settings.AGENT_MAX_ITERATIONS,
            enable_overlay=settings.AGENT_ENABLE_OVERLAY,
            dry_run=settings.AGENT_DRY_RUN,
            omniparser_url=settings.HF_OMNIPARSER_URL,
            omniparser_token=settings.HF_API_TOKEN,
            qwen_api_key=settings.QWEN_API_KEY,
            qwen_api_base=settings.QWEN_API_BASE,
            qwen_model=settings.QWEN_MODEL,
            qwen_temperature=settings.QWEN_TEMPERATURE,
        )
        agent_result = engine.run(prompt, file_path=file_path, clarifications=clarifications)
        result_payload = {
            "final_message": agent_result.final_message,
            "actions": agent_result.actions,
            "screenshots": agent_result.screenshots,
            "elements": agent_result.elements,
            "plan": agent_result.plan,
            "log_path": agent_result.log_path,
        }
        status = agent_result.status
        pending_question = agent_result.pending_question
        if status == "needs_input":
            log("planner", "LLM requested additional user input")
        else:
            log("complete", "Agent finished successfully")
    except Exception as exc:
        log("error", str(exc))
        status = "error"
        result_payload = None
        pending_question = None

    log_path = LOG_DIR / f"{run_id}.json"
    with log_path.open("w", encoding="utf-8") as handle:
        json.dump([entry.model_dump() for entry in logs], handle, indent=2, default=str)

    return {
        "run_id": run_id,
        "status": status,
        "logs": logs,
        "result": result_payload,
        "log_path": str(log_path),
        "pending_question": pending_question,
    }
