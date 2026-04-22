# Blackbird Server

## Overview

This is the backend server for the **Blackbird** project, built with **FastAPI** and **PostgreSQL**.
It provides the API endpoints, business logic, sentiment analysis, relevancy score, and background scraping services needed for the application, using **SQLModel** as the ORM.

---

## Features

- **FastAPI** backend with modular structure.
- **SQLModel** ORM for type-safe database interactions.
- **PostgreSQL** persistence with Docker volumes.
- Automated database initialization and seeding.
- Environment variable support via `.env`.
- Dockerized for consistent development and deployment.
- Query based web scraping. 
- Calculate sentiment and relevancy score statistics. 

## Prerequisites

Before running the backend, ensure you have the following installed:

- **Docker Engine** (Linux) or **Docker Desktop** (Windows / Mac)
  - [Install Docker](https://docs.docker.com/get-docker/)
- For Windows, **Install WSL**
  ```powershell
      wsl --install
  ```
- **Proxies** Not required, but highly recommended
  - We recommend using [webshare.io](https://www.webshare.io/)
    - If using webshare.io for proxies, use this [notebook](https://colab.research.google.com/drive/11h7IZ1pFneZYvHI5i5ueLVokznMcCHH5?usp=sharing) to easily convert exported csv file to json for .env file

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
│   ├── core/                     # Account
│   │   └── security.py           # Accounts and Security
│   │
│   ├── models/                   # SQLModel ORM entities (Table definitions)
│   │   ├── __init__.py           # Central export for metadata registration
│   │   ├── search.py             # Search & Link tables
│   │   ├── source.py             # Scraper source registry & Enums
│   │   ├── article.py            # Article data & constraints
│   │   ├── user.py               # User information
│   │   └── proxy.py              # Proxy management & logs
│   │
│   ├── db/                       # Database configuration
│   │   ├── session.py            # Engine & Session management
│   │   ├── populate_test_data.py # CLI tool for populating test data
│   │   ├── init.py               # Table creation & initial seeding
│   │   └── inspect_data.py       # CLI tool to view table entries
│   │
│   ├── ml/                       # Machine Learning/Sentiment analysis 
│   │   ├── NewsSentiment.py      # Sentiment analysis pipeline
│   │   └── cleaner.py            # Relevance score
│   │
│   ├── services/                 # Business logic layer
│   │   ├── auth_service.py       # Authentication service
│   │   ├── search_service.py     # Produces data for search endpoint
│   │   └── summary_service.py    # Produces data for summary endpoint
│   │
│   ├── workers/                  # Background scrapers (Social/News/Gov)
│   │   ├── core/                 # Browser, parent, and proxy management 
│   │   └── scrapers/             # (Social/News/Gov) Scrapers
│   │
│   └── utils/                    # Shared helper utilities
│       ├── workers_utils.py      # Scraping utilities
│       ├── boolean_utils.py      # Boolean query support
│       └── metadata_utils.py     # Source helpers 
│
├── scripts/                      # Scripts for Git Actions
├── tests/                        # Testing suite
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
### Added quick version of startup commands
Quick start commands for Unix based systems: 
```bash 
sudo docker compose up -d --build
sudo docker compose exec backend python3 -m app.db.init
sudo docker compose exec backend python3 -m app.db.inspect_data
```
Quick start commands for Windows based systems:
```bash
wsl
cd <navigate_to_project_file> 
docker compose up -d --build
docker compose exec backend python3 -m app.db.init
docker compose exec backend python3 -m app.db.inspect_data
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