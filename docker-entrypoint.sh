#!/bin/sh
# ===================================================================
#  Runs every time the container starts.
# ===================================================================
set -e    # stop at the first failure, so a broken start never serves traffic

echo "Applying database changes..."
python manage.py migrate --noinput

# Loads the demo data the first time only. On every later start it sees the
# existing data, prints a note and does nothing -- it never wipes anything.
echo "Checking demo data..."
python manage.py seed_demo

echo "Starting SkillScope on port ${PORT:-10000}..."
# exec hands the process over to gunicorn, so Render's stop signal reaches it
# directly and shuts it down cleanly.
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
