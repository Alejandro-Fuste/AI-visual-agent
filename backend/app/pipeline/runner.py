from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.agent.engine import VisualAgentEngine
from app.config import settings
from app.schemas import LogEntry


def run_full_pipeline(
    run_id: str,
    prompt: str,
    file_path: Optional[str] = None,
    clarifications: Optional[List[str]] = None,
    run_dir: Optional[Path] = None,
):
    logs: list[LogEntry] = []

    def log(stage: str, message: str) -> None:
        entry = LogEntry(stage=stage, message=message, timestamp=datetime.utcnow())
        logs.append(entry)
        print(f"[{stage}] {message}")

    log("init", f"Pipeline started for prompt: {prompt}")

    run_root = Path(run_dir) if run_dir else settings.AGENT_RUNS_DIR / run_id
    screenshots_dir = run_root / "screenshots"
    actions_log_dir = run_root / "logs"
    pipeline_log_dir = run_root / "pipeline"
    for path in [run_root, screenshots_dir, actions_log_dir, pipeline_log_dir]:
        path.mkdir(parents=True, exist_ok=True)

    try:
        engine = VisualAgentEngine(
            run_id,
            screenshot_dir=screenshots_dir,
            log_dir=actions_log_dir,
            max_iterations=settings.AGENT_MAX_ITERATIONS,
            enable_overlay=settings.AGENT_ENABLE_OVERLAY,
            dry_run=settings.AGENT_DRY_RUN,
            omniparser_url=settings.HF_OMNIPARSER_URL,
            omniparser_token=settings.HF_API_TOKEN,
            qwen_api_key=settings.QWEN_API_KEY,
            qwen_api_base=settings.QWEN_API_BASE,
            qwen_model=settings.QWEN_MODEL,
            qwen_temperature=settings.QWEN_TEMPERATURE,
            action_pause=settings.AGENT_ACTION_PAUSE,
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

    pipeline_log_path = pipeline_log_dir / "pipeline.json"
    with pipeline_log_path.open("w", encoding="utf-8") as handle:
        json.dump([entry.model_dump() for entry in logs], handle, indent=2, default=str)

    return {
        "run_id": run_id,
        "status": status,
        "logs": logs,
        "result": result_payload,
        "log_path": str(pipeline_log_path),
        "pending_question": pending_question,
    }
