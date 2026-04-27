# server/app/main.py
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, saved_search, search, summary

load_dotenv()
app = FastAPI(
    title="Capstone Backend",
    description="Backend API for aggregated search and analytics",
    version="0.1.0",
)

# Get origins from environment, default to localhost for dev
env_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")

# Allow CORS for frontend integration (adjust origins as needed)
# strips by comma if multiple
origins = [origin.strip() for origin in env_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Example root endpoint
@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to the team Blackbird server!"}


app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(summary.router, prefix="/api/v1/summary", tags=["summary"])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

app.include_router(saved_search.router, prefix="/api/v1/saved_search",
                   tags=["saved_search"])