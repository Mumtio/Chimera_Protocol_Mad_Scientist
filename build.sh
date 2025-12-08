#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers (chromium only to save space)
# This requires ~300MB disk space
echo "Installing Playwright Chromium browser..."
playwright install chromium --with-deps || echo "Playwright browser install skipped (optional)"

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create superuser if env vars are set (runs only once, skips if user exists)
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py create_superuser || true
fi
