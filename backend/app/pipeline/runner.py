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

        # Stage 1: Perception (YOLO / Omniparser)
        perception_output = perception.process_image(file_path)
        log("YOLO", f"Detected {len(perception_output.get('elements', []))} UI elements")

        # Stage 2: Reasoning (BLIP)
        reasoning_output = reasoning.analyze_elements(perception_output)
        log("BLIP", "Semantic reasoning complete")

        # Stage 3: LLM Decision (LangChain)
        llm_result = llm_agent.generate_actions(prompt, reasoning_output)
        log("LLM", "LLM completed action generation")

        status = "success"
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
