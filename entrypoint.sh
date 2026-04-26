#!/bin/bash
set -e

echo "Step 1/2: Initializing Database Schema & Seeding..."
# This runs your init.py logic
python3 -m app.db.init

echo "Step 2/2: Starting FastAPI Server..."
# Starts the actual API
exec uvicorn app.main:app --host 0.0.0.0 --port 8000