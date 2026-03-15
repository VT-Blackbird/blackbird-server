# Blackbird Server

## Overview

This is the backend server for the **Blackbird** project, built with **FastAPI**.  
It provides the API endpoints, business logic, and services needed for the application.

---

## Features

- FastAPI backend with modular structure
- Easy-to-extend routes and services
- Environment variable support via `.env`
- Dockerized for consistent development and deployment

## Prerequisites

Before running the backend, ensure you have the following installed:

- **Docker Engine** (Linux) or **Docker Desktop** (Windows / Mac)
  - https://docs.docker.com/get-docker/

---

## Project Structure

```plaintext
server/
│
├── app/                          # Main backend application package
│   │
│   ├── main.py                   # FastAPI application entrypoint
│   │
│   ├── api/                      # API layer (HTTP interface)
│   │   └── routes/               # Route definitions / controllers
│   │
│   ├── schemas/                  # Pydantic request/response models
│   │   └── search_request.py     # Example request schema
│   │
│   ├── models/                   # Database ORM models (tables/entities)
│   │
│   ├── repositories/             # Data access layer (DB queries & persistence)
│   │
│   ├── services/                 # Business logic layer
│   │                              # Orchestrates repositories, ML, and utilities
│   │
│   ├── db/                       # Database configuration and session management
│   │
│   ├── ml/                       # Machine learning & sentiment analysis logic
│   │                              # Models, inference pipelines, feature processing
│   │
│   ├── workers/                  # Background jobs (scraping, async processing)
│   │                              # Designed for scheduled or queue-based tasks
│   │
│   └── utils/                    # Shared helper utilities and common functions
│
├── scripts/                      # DevOps & Quality Control scripts
│   └── check.sh                  # THE GAUNTLET: Lint, Type Check, & Test
├── tests/                        # Automated Pytest suite
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # Backend environment definition
├── pyproject.toml                # Tool configurations (Ruff, MyPy)
└── requirements.txt              # Python dependencies


```

## Quality Standards

- Ruff: Enforces PEP 8 and import sorting.

- MyPy (Strict)
  - All function signatures must have type hints.
  - None returns and variables must be explicitly handled via Optional or guard clauses.
  - Implicit Any types are disallowed.
- Pytest: All logic in app/services and app/workers must have corresponding test coverage in tests/.

| Action              | Command | Notes                                            |
|---------------------|--------|--------------------------------------------------|
| Runs checks locally | `sudo ./scripts/check.sh` | Runs quality assurance tests (Ruff MyPy, PyTest( |
 | Fast formatting    |  ` sudo docker compose run --rm backend ruff check . --fix`| Fixes style errors fast|

## Docker

> The backend is fully containerized using Docker.  
> Running it inside a container ensures consistent environment, avoids dependency conflicts,
> and makes development and deployment identical across all machines.

### Docker Command Reference


| Action | Command | Notes |
|--------|--------|-------|
| Build backend image | `sudo docker compose build backend` | Creates or updates the image using the Dockerfile and requirements |
| Start container in background | `sudo docker compose up -d backend` | Runs container detached (in background); creates it if it doesn’t exist |
| Stop container | `sudo docker compose stop backend` | Stops container without deleting it |
| Restart container | `sudo docker compose restart backend` | Restarts container using existing image |
| Stop and remove containers | `sudo docker compose down` | Cleans up containers, networks, and default volumes |
| Rebuild image and recreate container | `sudo docker compose up -d --build backend` | Ensures container runs the latest image after changes |
| Run tests inside container | `sudo docker compose run --rm backend pytest` | Temporary container; removed after running |
| Run specific test file | `sudo docker compose run --rm backend pytest tests/test_specific.py` | Useful for targeted testing |
| Access shell in container | `sudo docker compose run --rm backend /bin/bash` | Temporary interactive shell in container |
| View running containers | `sudo docker ps` | Shows active containers |
| View all containers | `sudo docker ps -a` | Shows running and stopped containers |
| View images | `sudo docker images` | Lists all downloaded/built images |
| Remove an image | `sudo docker rmi <image_name>` | Deletes an image; container must not be using it |
