# server/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import search

app = FastAPI(
    title="Capstone Backend",
    description="Backend API for aggregated search and analytics",
    version="0.1.0",
)

# Allow CORS for frontend integration (adjust origins as needed)
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

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
