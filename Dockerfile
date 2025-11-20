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

# Copy pyproject.toml first for better layer caching
COPY pyproject.toml ./

# Copy application code
COPY . .

# Install application with dev dependencies in editable mode
RUN pip install --upgrade pip && \
    pip install -e .[dev]

# Default command for development
CMD ["python", "-m", "pytest"]

# Production stage
FROM base as production

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy pyproject.toml first for better layer caching
COPY --chown=appuser:appuser pyproject.toml ./

# Copy application code
COPY --chown=appuser:appuser src ./src

# Install production dependencies and application
RUN pip install --upgrade pip && \
    pip install .

# Switch to non-root user
USER appuser

# Default command (override in docker-compose.yml as needed)
CMD ["python", "-m", "sark"]
