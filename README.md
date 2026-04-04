# Blackbird Server

## Overview

This is the backend server for the **Blackbird** project, built with **FastAPI** and **PostgreSQL**.
It provides the API endpoints, business logic, and background scraping services needed for the application, using **SQLModel** as the ORM.

---

## Features

- **FastAPI** backend with modular structure.
- **SQLModel** ORM for type-safe database interactions.
- **PostgreSQL** persistence with Docker volumes.
- Automated database initialization and seeding.
- Environment variable support via `.env`.
- Dockerized for consistent development and deployment.

## Prerequisites

Before running the backend, ensure you have the following installed:

- **Docker Engine** (Linux) or **Docker Desktop** (Windows / Mac)
  - [Install Docker](https://docs.docker.com/get-docker/)
- **Git Large File Storage**
  - Linux Command: sudo apt-get install git-lfs
  - Windows: winget install GitHub.GitLFS
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
│   ├── models/                   # SQLModel ORM entities (Table definitions)
│   │   ├── __init__.py           # Central export for metadata registration
│   │   ├── search.py             # Search & Link tables
│   │   ├── source.py             # Scraper source registry & Enums
│   │   ├── article.py            # Article data & constraints
│   │   └── proxy.py              # Proxy management & logs
│   │
│   ├── db/                       # Database configuration
│   │   ├── session.py            # Engine & Session management
│   │   ├── init.py               # Table creation & initial seeding
│   │   └── inspect_data.py       # CLI tool to view table entries
│   │
│   ├── services/                 # Business logic layer
│   ├── workers/                  # Background scrapers (Social/News/Gov)
│   └── utils/                    # Shared helper utilities
│
├── docker-compose.yml            # Orchestrates Backend + PostgreSQL
├── Dockerfile                    # Backend environment definition
├── env_example.txt               # Template for environment variables
└── requirements.txt              # Python dependencies
```

---

## Setup & Configuration

### 1. Environment Variables
Refer to `env_example.txt` for the required keys and authentication info. You should create or update your local `.env` file manually to ensure the database credentials match your local setup without overwriting other personal environment arguments.

*Note: If you change `DB_PASSWORD` after the database is already initialized, you must wipe the volume (see Persistence section below).*

### 2. Database Initialization
Once the containers are running, you can initialize the schema and seed the initial scraper sources:
```bash
sudo docker compose exec backend python3 -m app.db.init
```

Note: This functionality will likely be hooked into the `main.py` file in the future

### 3. Inspecting Data
To quickly verify the contents of the tables (first 5 entries) without a GUI:
```bash
sudo docker compose exec backend python3 -m app.db.inspect_data
```
Currently, this should show all tables as empty except for the initial source table entries.

### 4. Populating Data for Testing
To populate the database with test data, you can run the following command:
```bash
sudo docker compose exec backend python3 -m app.db.populate_test_data
```
This currently adds 9 example articles (3 per scraper) from the query "Artificial Intelligence". Running the inspection command again will show these entries in the database in the Search and Article tables.

To delete the test data, you can run:
```bash
sudo docker compose exec backend python3 -m app.db.populate_test_data --clear
```
---

## Data Persistence & Volumes

The database uses a Docker volume named `postgres_data` to ensure searches and articles persist even if containers are stopped or rebuilt.

| Command | Effect on Data |
|---------|----------------|
| `docker compose stop` | **Safe**: Data is preserved. |
| `docker compose down` | **Safe**: Data is preserved. |
| `docker compose down -v` | **WIPED**: Deletes the volume and all stored data. |

---
## Git Large File Storage Commands
More information on git-lfs commands can be found in the tutorial [here](https://medium.com/@pablojusue/git-lfs-and-dvc-the-ultimate-guide-to-managing-large-artifacts-in-mlops-c1c926e6c5f4 
). Git-lfs stores large files as pointers. Once a file is tracked, make sure to add .gitattributes to the commit then you can use git as normal. 

|Action |Command| Notes|
|-------|--------|------|
|Add a file to git-lfs | `git lfs track <file-path>` |
| Add gitattributes to git| `git add .gitattributes`| must commit where tracking info is from 
|View all files recognized as "tracked"| `git lfs ls-files`|
|View all patterns you are tracking|`git lfs track`|


---

## Quality Standards

- **Ruff**: Enforces PEP 8 and import sorting.
- **MyPy (Strict)**
  - All function signatures must have type hints.
  - None returns and variables must be explicitly handled via Optional or guard clauses.
  - Implicit Any types are disallowed.
- **Pytest**: All logic in `app/services` and `app/workers` must have corresponding test coverage in `tests/`.
- **SQLModel**: Ensures that our database entities match our Python types exactly.

| Action | Command | Notes |
| :--- | :--- | :--- |
| Runs checks locally | `sudo docker compose run --rm backend bash scripts/check.sh` | Runs quality assurance tests (Ruff, MyPy, PyTest) |
| Fast formatting | `sudo docker compose run --rm backend ruff check . --fix` | Fixes style errors fast |
| Code Coverage | `sudo docker compose run --rm backend bash scripts/coverage.sh` | Fails if < 60%. Used as a gate for production. |

---

## Docker

> The backend is fully containerized using Docker.  
> Running it inside a container ensures a consistent environment, avoids dependency conflicts, and makes development and deployment identical across all machines.

### Docker Command Reference

| Action | Command | Notes |
| :--- | :--- | :--- |
| Build backend image | `sudo docker compose build backend` | Creates or updates the image using the Dockerfile and requirements |
| Start stack (detached) | `sudo docker compose up -d` | Runs full stack in background; creates containers if they don’t exist |
| Stop services | `sudo docker compose stop` | Stops containers without deleting them |
| Restart backend | `sudo docker compose restart backend` | Restarts container using existing image |
| Stop and remove | `sudo docker compose down` | Cleans up containers, networks, and default volumes |
| Rebuild and recreate | `sudo docker compose up -d --build` | Ensures container runs the latest image after code/dependency changes |
| Run tests | `sudo docker compose run --rm backend pytest` | Temporary container; removed after running |
| Run specific test | `sudo docker compose run --rm backend pytest tests/test_specific.py` | Useful for targeted testing |
| Access container shell | `sudo docker compose exec backend /bin/bash` | Open interactive shell in a running container |
| View DB logs | `sudo docker compose logs -f db` | Useful for monitoring database initialization or connection issues |
| View running containers | `sudo docker ps` | Shows active containers |
| Access Postgres CLI | `sudo docker compose exec db psql -U postgres -d blackbird` | Directly query the database from the terminal |