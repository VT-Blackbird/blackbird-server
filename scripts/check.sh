#!/bin/bash
set -e

# Function to run a command either via docker or directly
run_cmd() {
  if [ -f /.dockerenv ]; then
    $@
  else
    docker compose run --rm backend $@
  fi
}

echo "---- 1. Running Linter (Ruff) ----"
run_cmd ruff check .

echo "---- 2. Running Type Checker (MyPy) ----"
run_cmd mypy app tests \
  --ignore-missing-imports \
  --follow-imports=skip \
  --disable-error-code=misc \
  --disable-error-code=attr-defined \
  --disable-error-code=call-arg \
  --disable-error-code=no-any-return \
  --disable-error-code=union-attr

echo "---- 3. Running Tests (Pytest) ----"
run_cmd pytest