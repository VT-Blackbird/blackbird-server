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
