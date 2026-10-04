# Production Dockerfile for SerpApi Job & Market Radar
FROM python:3.11-slim

# Prevent Python from writing bytecode and enable instant logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install curl for container healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY app/ ./app/
COPY static/ ./static/
COPY data/ ./data/
COPY run.py .

# Expose HTTP port
EXPOSE 8000

# Healthcheck probe for orchestrators (Render, HuggingFace, Fly.io, Railway)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run Uvicorn ASGI server with single-worker production binding
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
