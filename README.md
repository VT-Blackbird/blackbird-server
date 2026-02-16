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

---

## Project Structure

```plaintext
server/
│
├── app/                      # Main application package
│   ├── main.py               # FastAPI entrypoint
│   ├── routes/               # API endpoints (controllers)
│   └── services/             # Business logic layer
│
├── .env                      # Environment variables (not committed)
├── requirements.txt          # Python dependencies
└── .gitignore

```

## Docker

- Used to ensure consistent environment regardless of operating system

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
