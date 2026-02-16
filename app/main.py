# server/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your routes (you can create them later)
# from app.routes import search, summary

app = FastAPI(
    title="Capstone Backend",
    description="Backend API for aggregated search and analytics",
    version="0.1.0"
)

# Allow CORS for frontend integration (adjust origins as needed)
origins = [
    "http://localhost:3000",  # your React frontend
    # Add other origins if necessary
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
async def root():
    return {"message": "Welcome to team Blackbird!!"}

# Include routers from your routes folder (to be added later)
# app.include_router(search.router, prefix="/search", tags=["Search"])
# app.include_router(summary.router, prefix="/summary", tags=["Summary"])
