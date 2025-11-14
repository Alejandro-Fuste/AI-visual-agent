#!/bin/bash
# Start the FastAPI backend server

cd "$(dirname "$0")"

# Activate virtual environment
source ../.venv-web-system/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start uvicorn server
echo "🚀 Starting Visual Agent Backend on http://${HOST:-0.0.0.0}:${PORT:-8080}"
echo "📡 Connecting to LLM API at ${LLM_API_URL:-http://127.0.0.1:5000}"
echo ""

uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}" --reload
