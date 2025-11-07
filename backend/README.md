# Visual Agent Backend

The **Visual Agent Backend** powers the core AI pipeline for the Visual Agent project.
It serves as the connection between the **frontend web app** and the **computer-vision / reasoning modules** built with Python and FastAPI.

---

## Folder Overview

```
backend/
│
├── app/
│   ├── pipeline/           # Core AI pipeline modules
│   │   ├── llm_agent.py     # Language reasoning + response generation
│   │   ├── perception.py    # Handles image analysis or YOLO detection
│   │   ├── reasoning.py     # High-level logic for connecting perception + LLM
│   │   └── runner.py        # Pipeline entry point that orchestrates all modules
│   │
│   ├── routers/            # FastAPI route definitions
│   │   ├── health.py        # Simple health check endpoint (/health)
│   │   └── pipeline.py      # Main routes for running and tracking pipeline tasks
│   │
│   ├── config.py           # Environment + application configuration
│   ├── logging_config.py   # Centralized logging setup
│   ├── main.py             # FastAPI entry point (creates the app)
│   └── schemas.py          # Pydantic models for request / response validation
│
├── logs/                   # Runtime logs generated during execution
├── uploads/                # Temporary upload directory for input files
│
├── .env.example            # Template for environment variables
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## Quick Start Guide

### 1. Clone the Repository

If this backend is part of a larger repo, go to the backend folder:

```bash
git clone <repo-url>
cd backend
```

---

### 2. Set Up a Virtual Environment

Python ≥ 3.10 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# or
.venv\Scripts\activate      # Windows
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Then open `.env` and update any paths or API keys if needed (e.g. OpenAI, Hugging Face, etc.).

---

### 5. Run the Server Locally

Use **Uvicorn** to start the FastAPI app:

```bash
uvicorn app.main:app --reload --port 8000
```

Your backend will be available at
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## API Endpoints

| Endpoint               | Method | Description                                                        |
| ---------------------- | ------ | ------------------------------------------------------------------ |
| `/health`              | GET    | Basic server health check                                          |
| `/api/run`             | POST   | Starts a new AI pipeline run (accepts text prompt + optional file) |
| `/api/status/{run_id}` | GET    | Checks status and logs for a given pipeline run                    |
| `/api/reprompt`        | POST   | Allows LLM to request additional user input                        |

---

## How the Pipeline Works

1. **Frontend Request** → The web app sends a prompt or file to `/api/run`.
2. **Runner** → The `runner.py` module coordinates calls to:

   * `perception.py` → detects elements (e.g. via YOLO or vision model)
   * `reasoning.py` → interprets results logically
   * `llm_agent.py` → generates final explanations or actions
3. **Logging** → Results are streamed back incrementally through `/api/status/{run_id}`.
4. **Reprompt** → The LLM can re-query the user for missing information.

---

## Logs & Uploads

* All user-uploaded files are stored temporarily in `/uploads`.
* Pipeline and runtime logs are stored in `/logs`.

These directories are **auto-created** when running locally.

---

## Development Notes

* Framework: **FastAPI**
* Server: **Uvicorn**
* Logging: Configured in `logging_config.py`
* Pydantic models: Defined in `schemas.py`
* Modular design: Each subsystem (perception, reasoning, llm_agent) is separated for clarity.

---

## Testing the API

### Run Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Run a Sample Pipeline

```bash
curl -X POST "http://127.0.0.1:8000/api/run" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fill out login form"}'
```

### Check Run Status

```bash
curl http://127.0.0.1:8000/api/status/<run_id>
```

---

## Team Notes

* Keep all experimental models or heavy dependencies inside the `/pipeline` sub-modules.
* Do **not** commit real `.env` secrets — only `.env.example` should be versioned.
* The backend is designed to integrate seamlessly with the **Visual Agent frontend** (React + Vite) via `http://localhost:8000`.

---

## Next Steps

* [ ] Add real-time log updates (via WebSocket instead of polling).
* [ ] Implement re-prompting UI (backend triggers a frontend modal when the LLM needs clarification).
* [ ] Replace the mock modules with real pipeline (YOLO, BLIP, LangChain).

---

## Documentation

Once the backend is running, visit:

🔗 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
for the **interactive API documentation** generated by FastAPI.

---

