# Women's Safety Response — OpenEnv Docker Image
# Compatible with HuggingFace Spaces (port 7860)

FROM python:3.11-slim

LABEL maintainer="Women Safety OpenEnv Team"
LABEL description="OpenEnv environment for women's safety emergency response tasks"
LABEL org.opencontainers.image.title="womens-safety-response"
LABEL org.opencontainers.image.version="1.0.0"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY tasks/ ./tasks/
COPY openenv.yaml .
COPY inference.py .

# Fix ownership
RUN chown -R appuser:appuser /app

USER appuser

# HuggingFace Spaces uses port 7860
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
