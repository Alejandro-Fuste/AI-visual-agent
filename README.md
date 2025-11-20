# AI-visual-agent

Visual Agent is an AI-powered web application that automates desktop workflows using OmniParser + GPT-5. The backend (FastAPI + PyAutoGUI) perceives the current screen, plans actions via GPT tool-calling, and executes clicks/typing while logging every step. A React frontend lets you submit tasks, watch status updates, and respond to clarification requests.

## Prerequisites
- Windows or macOS desktop session (PyAutoGUI + overlay need a GUI; set `AGENT_DRY_RUN=true` for headless testing)
- Python 3.10+
- Node.js 18+
- API access to your hosted OmniParser endpoint (Hugging Face Inference) and OpenAI (GPT-4o/GPT-5 family)

## Backend setup
```bash
python -m venv .venv
.venv\Scripts\activate  # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt  # installs backend/requirements.txt
```

Create `backend/.env` (copy from `backend/.env.example`) and fill in:

```
HF_OMNIPARSER_URL=...
HF_API_TOKEN=...
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5.1-mini
OPENAI_TEMPERATURE=0.0
AGENT_MAX_ITERATIONS=5
AGENT_ENABLE_OVERLAY=true
```

Then run the backend:

```bash
cd backend
uvicorn app.main:app --reload
```

## Frontend setup
```bash
cd frontend
npm install
echo "VITE_API_URL=http://127.0.0.1:8000" > .env
npm run dev
```

Visit `http://localhost:5173`, enter a task, and hit **Go**. The backend will:
1. Capture the current desktop screenshot.
2. Call OmniParser for bounding boxes/labels.
3. Feed the structured elements to GPT-5 via tool-calling to obtain an action plan.
4. Execute the actions with PyAutoGUI, annotate the screen, and log everything.
5. Return status/log/screenshot updates to the UI. If GPT requests clarification, the frontend opens a modal so you can respond.

Run artifacts live under `runtime/runs/<timestamp>-<slug>/`:
- `screenshots/` – before/after frames
- `logs/actions.log` – timestamped PyAutoGUI actions
- `logs/omniparser/` – OmniParser debug overlays
- `pipeline/pipeline.json` – FastAPI stage logs

<!-- ## Packaging for others
1. Share the repo (or zip) without real `.env` files. Include `backend/.env.example` and `frontend/.env.example`.
2. Document the steps above in your README (already here).
3. Remind users to run `pip install -r requirements.txt` and `npm install`, set their own API keys, then launch backend + frontend concurrently.

## Notes
- `runtime/runs/*` accumulates per-task data; you can clear it anytime for privacy.
- For production, move secrets to a vault and consider replacing the in-memory RUNS store with Redis/Postgres. -->
