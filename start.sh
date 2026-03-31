#!/bin/bash
# Start the ColabDoc backend (which also serves the frontend)
cd "$(dirname "$0")/backend"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
