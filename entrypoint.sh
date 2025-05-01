#!/bin/bash

set -e

echo "Running migrations..."
PYTHONUNBUFFERED=1 alembic upgrade head

echo "Migrations finished"
exec python -m src.bot