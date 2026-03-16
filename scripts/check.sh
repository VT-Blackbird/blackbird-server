#!/bin/bash
set -e

# Function to run a command either via docker or directly
run_cmd() {
  if [ -f /.dockerenv ]; then
    # We are ALREADY inside a container, run directly
    $@
  else
    # We are on a host machine, use docker compose
    docker compose run --rm backend $@
  fi
}

echo "---- 1. Running Linter (Ruff) ----"
run_cmd ruff check .

echo "---- 2. Running Type Checker (MyPy) ----"
run_cmd mypy app tests

echo "---- 3. Running Tests (Pytest) ----"
run_cmd pytest