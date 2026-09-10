# ===================================================================
#  SkillScope - production image
#
#  Build:   docker build -t skillscope .
#  Run:     see docker-entrypoint.sh, and render.env.example for the
#           values the container needs.
# ===================================================================

# Same Python minor version the project is developed and tested on.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Switches on everything a public deployment needs -- see config/settings.py.
    SKILLSCOPE_PRODUCTION=1

WORKDIR /app

# Dependencies first, on their own layer. Rebuilding after a code change then
# reuses this layer instead of reinstalling every package.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Gather the CSS, JavaScript and fonts into one folder, with fingerprinted
# names that browsers can cache forever.
#
# Production settings refuse to start without a secret key, a Cloudinary URL
# and a public address -- deliberately, so a misconfigured deploy fails loudly.
# collectstatic needs none of them, so throwaway placeholders are passed for
# this ONE command only. They are not stored in the image; the real values are
# supplied by Render when the container starts.
RUN SKILLSCOPE_SECRET_KEY=build-time-placeholder-never-used-at-runtime \
    CLOUDINARY_URL=cloudinary://0:placeholder@build-time \
    SKILLSCOPE_SITE_URL=https://build.invalid \
    python manage.py collectstatic --noinput

# Run as an ordinary user rather than root, so a flaw in the app cannot be
# used to take over the whole container.
RUN useradd --create-home --uid 1000 skillscope \
    && chmod +x docker-entrypoint.sh \
    && chown -R skillscope:skillscope /app
USER skillscope

# Render tells the container which port to listen on through $PORT.
EXPOSE 10000

CMD ["./docker-entrypoint.sh"]
