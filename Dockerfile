# Lightweight Python image for fast startup
FROM python:3.11-slim

# Metadata
LABEL maintainer="ASL ML API"
LABEL description="FastAPI ML inference server for ASL sign language recognition"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directory for models
RUN mkdir -p /models

# Non-root user for security
RUN useradd -m -u 1000 aslapi && chown -R aslapi:aslapi /app /models
USER aslapi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

