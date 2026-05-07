# ── Babel Backend Dockerfile ─────────────────────────────────────────────────
# CUDA 12.8 + Python 3.11 — matches local dev environment
# Runs faster-whisper with GPU acceleration
# ─────────────────────────────────────────────────────────────────────────────

FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

# Prevent interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 babel
WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Switch to non-root user
USER babel

EXPOSE 8000

# Health check — ensures the container is considered healthy before receiving traffic
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
