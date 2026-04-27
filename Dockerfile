# ===============================
# Dockerfile for FastAPI Backend
# ===============================

# 1. Use a stable Python image
FROM python:3.12-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy dependency files first for caching
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# 5. Copy the rest of the application
COPY . .

# 6. Expose the port FastAPI will run on
EXPOSE 8000

# 7. Set environment variables
#    This allows us to use .env values at runtime if needed
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 8. Set the Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
