# Visual Agent Backend

FastAPI service that exposes the visual agent pipeline to the frontend. It wraps the following subsystems:

1. **Perception** – grabs screenshots (or uploaded files) and calls the hosted OmniParser endpoint via `omniparser_tool.OmniParserClient`.
2. **Planning** – feeds screenshots, parsed elements, and action history to Qwen through an OpenAI-compatible API, requesting structured JSON plans.
3. **Action execution** – dispatches each planned tool to `AgentToolbox` (PyAutoGUI-based desktop controller) which also renders overlays, captures new screenshots, and logs every action.
4. **Conversation loop** – orchestrated inside `app/agent/engine.py` with configurable iterations. If Qwen asks for clarification it pauses, waits for `/api/reprompt`, then resumes with the extra context.

## Environment
See `.env.example` for the required variables:

- `HF_OMNIPARSER_URL` / `HF_API_TOKEN`
- `QWEN_API_KEY`, `QWEN_API_BASE`, `QWEN_MODEL`, `QWEN_TEMPERATURE`
- Agent behavior toggles (`AGENT_MAX_ITERATIONS`, `AGENT_ENABLE_OVERLAY`, `AGENT_DRY_RUN`, `AGENT_ACTION_PAUSE`)
- Storage root: `AGENT_RUNS_DIR` (default `runtime/runs`) which holds per-run `screenshots`, `logs`, `pipeline`, and `uploads` folders.

Create `.env`, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API
| Endpoint | Verb | Description |
| --- | --- | --- |
| `/health` | GET | Basic health probe |
| `/api/run` | POST (multipart) | Starts an agent run with `prompt` and optional file upload. Returns `run_id`. |
| `/api/status/{run_id}` | GET | Poll run status, logs, final result, and pending questions. |
| `/api/reprompt` | POST | Submit additional user input when the agent status is `needs_input`. |

`StatusResponse.result` contains:
- `final_message` – Qwen's natural language summary
- `actions` – serialized `ActionRecord`s (action, coords, metadata)
- `screenshots` – paths for screenshots captured during the run
- `plan` – raw planner output (thinking + full action JSON)

## Directories
- `app/agent/` – engine + planner client + dataclasses
- `app/pipeline/runner.py` – FastAPI-friendly wrapper that writes run logs
- `runtime/runs/<run_id>/screenshots` – captured evidence for that run
- `runtime/runs/<run_id>/logs` – action log + status records
- `runtime/runs/<run_id>/pipeline` – serialized FastAPI log history
- `runtime/runs/<run_id>/uploads` – any files provided with the request

## Reprompt Flow
When `needs_input` is returned, the backend stores the pending question and returns it via `/api/status`. The frontend opens a modal; once the user responds, the answer is appended to the run's clarification list and the pipeline restarts automatically with the same screenshot/file inputs.

## Testing Tips
- Set `AGENT_DRY_RUN=true` to exercise the full pipeline without sending PyAutoGUI events.
- Disable overlays via `AGENT_ENABLE_OVERLAY=false` if the host lacks a Qt-compatible display.
- Inspect `runtime/runs/<run_id>/logs/actions.log` to verify the action order that Qwen produced.
