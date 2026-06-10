#!/usr/bin/env bash
# Exit on error
set -o errexit

# Run Celery worker in the background
echo "Starting Celery background worker..."
celery -A app.workers.tasks.celery_app worker --loglevel=info &

# Run Uvicorn API server in the foreground
echo "Starting Uvicorn API server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
