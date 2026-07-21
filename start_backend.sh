#!/bin/bash
# Always execute from the project root
cd "$(dirname "$0")"

echo "Starting FastAPI Backend..."
source backend/venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
