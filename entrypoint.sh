#!/bin/bash
set -e

# --- Wait for Postgres to be ready ---
echo "Waiting for database on db:5432..."
until python3 -c "import socket; s = socket.socket(); s.connect(('db', 5432))" 2>/dev/null; do
  echo "Database is still unavailable - sleeping..."
  sleep 2
done

echo "Database is UP!"

echo "Step 1/2: Initializing Database Schema & Seeding..."
python3 -m app.db.init

# --- UPDATED Step 2/2: Run the passed command or default to Uvicorn ---
if [ $# -eq 0 ]; then
    echo "Step 2/2: No command provided, starting FastAPI Server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    echo "Step 2/2: Running custom command: $@"
    exec "$@"
fi