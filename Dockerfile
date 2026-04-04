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


#install dependency for ML model
RUN playwright install --with-deps
# 5. Copy the rest of the application
COPY . .

# 6. Expose the port FastAPI will run on
EXPOSE 8000

# 7. Set environment variables
#    This allows us to use .env values at runtime if needed
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 8. Command to run FastAPI using uvicorn
#    This will reload automatically in dev if you mount the code
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
