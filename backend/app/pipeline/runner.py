from datetime import datetime
from app.schemas import LogEntry
from app.pipeline import perception, reasoning, llm_agent
import uuid
import json
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def run_full_pipeline(prompt: str, file_path: str | None = None):
    run_id = str(uuid.uuid4())
    logs: list[LogEntry] = []

    def log(stage, msg):
        entry = LogEntry(stage=stage, message=msg, timestamp=datetime.utcnow())
        logs.append(entry)
        print(f"[{stage}] {msg}")

    try:
        log("init", f"Pipeline started for prompt: {prompt}")

        # Stage 1: Perception (Load OmniParser analysis)
        perception_output = perception.process_image(file_path)
        log("OmniParser", f"Loaded pre-processed UI analysis")

        # Stage 2: Reasoning (Pass through analysis)
        reasoning_output = reasoning.analyze_elements(perception_output)
        log("Reasoning", "Analysis prepared for LLM")

        # Stage 3: LLM Decision (Send to LLM API at port 5000)
        llm_result = llm_agent.generate_actions(prompt, reasoning_output)
        
        if llm_result.get("status") == "success":
            log("LLM", f"Action plan generated using {llm_result.get('model', 'LLM')}")
        else:
            log("LLM", f"LLM error: {llm_result.get('error', 'Unknown error')}")

        status = llm_result.get("status", "success")
        result = llm_result

    except Exception as e:
        log("error", str(e))
        status = "error"
        result = None

    # Save logs to file
    log_path = os.path.join(LOG_DIR, f"{run_id}.json")
    with open(log_path, "w") as f:
        json.dump([entry.model_dump() for entry in logs], f, indent=2, default=str)

    return {"run_id": run_id, "status": status, "logs": logs, "result": result, "log_path": log_path}
