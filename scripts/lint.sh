#!/bin/bash
set -e

echo "--- 1. Running Linter (Ruff) ---"
docker compose run --rm backend ruff check .

echo "--- 2. Running Type Checker (MyPy) ---"
# Just point to the directories; pyproject.toml handles the rest
docker compose run --rm backend mypy app tests

echo "--- 3. Running Tests (Pytest) ---"
docker compose run --rm backend pytest