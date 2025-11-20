# Base image with Python 3.11
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Copy requirements first for better layer caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements-dev.txt

# Copy application code
COPY . .

# Install application in editable mode
RUN pip install -e .

# Default command for development
CMD ["python", "-m", "pytest"]

# Production stage
FROM base as production

# Copy only production requirements
COPY requirements.txt ./

# Install production dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser pyproject.toml ./

# Install application
RUN pip install .

# Switch to non-root user
USER appuser

# Default command (override in docker-compose.yml as needed)
CMD ["python", "-m", "sark"]
