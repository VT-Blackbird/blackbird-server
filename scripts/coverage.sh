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

echo "---- Running Tests with Coverage (Min 60%) ----"
# --cov-fail-under=60: The script will exit with an error if coverage < 60%
run_cmd pytest --cov=app --cov-report=term-missing --cov-fail-under=60