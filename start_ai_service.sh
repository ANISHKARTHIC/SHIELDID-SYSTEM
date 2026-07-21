#!/bin/bash
# Move into the ai-service folder
cd "$(dirname "$0")/ai-service"

echo "Starting AI Microservice..."
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
