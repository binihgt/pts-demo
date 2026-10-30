# PTS Demo - Production Container Image
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (curl for healthchecks, sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user for security
RUN groupadd -g 1000 ptsgroup && \
    useradd -u 1000 -g ptsgroup -s /bin/bash -m ptsuser

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create instance and backup directories with correct ownership
RUN mkdir -p /app/instance /app/backups && \
    chown -R ptsuser:ptsgroup /app

# Switch to unprivileged user
USER ptsuser

# Expose default HTTP port
EXPOSE 5000

# Default command: Gunicorn WSGI server for the web dashboard
CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:5000", "--access-logfile=-", "--error-logfile=-", "wsgi:app"]
