#!/bin/bash
set -e

# CASPER Prime Docker Entry Point
echo "Starting CASPER Prime..."

# Wait for dependencies
echo "Waiting for database..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "Database is ready!"

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
cd /app
python -m alembic upgrade head

# Initialize CASPER configuration if not exists
if [ ! -f ".casper/config/casper.json" ]; then
    echo "Initializing CASPER configuration..."
    python -m core.cli init --skip-interactive
fi

# Start the application
echo "Starting CASPER Prime server..."
exec python -m uvicorn core.server:app \
    --host 0.0.0.0 \
    --port 8742 \
    --workers ${WORKERS:-1} \
    --log-level ${LOG_LEVEL:-info}