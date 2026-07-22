# CASPER Prime Dockerfile
# Multi-stage build for production deployment

# Stage 1: Frontend Build
FROM node:18-alpine as frontend-builder

WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci --only=production

COPY dashboard/ ./
RUN npm run build

# Stage 2: Python Backend Build
FROM python:3.11-slim as backend-builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-dev

# Stage 3: Production Image
FROM python:3.11-slim

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash casper

WORKDIR /app

# Copy Python dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=backend-builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY core/ ./core/
COPY templates/ ./templates/
COPY config/ ./config/

# Copy frontend build
COPY --from=frontend-builder /app/dashboard/dist/ ./dashboard/dist/

# Create necessary directories
RUN mkdir -p .casper/context .casper/config .casper/output logs && \
    chown -R casper:casper /app

# Switch to non-root user
USER casper

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Expose ports
EXPOSE 8742 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8742/health || exit 1

# Start script
COPY docker-entrypoint.sh /app/
USER root
RUN chmod +x /app/docker-entrypoint.sh
USER casper

ENTRYPOINT ["/app/docker-entrypoint.sh"]