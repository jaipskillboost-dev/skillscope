"""
Settings for SkillScope.

Everything a person needs to change to run this on another machine is in the
SETUP section at the top. Nothing below that section normally needs editing.
"""

import os
import sys
from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Local settings file
#
# If a ".env" file sits next to manage.py, its values are loaded here before
# anything below reads them. That file is written by the Setup option when it
# asks for your MySQL password, so the password is remembered between runs
# instead of having to be typed every time.
#
# It is listed in .gitignore, so your password is never shared or committed.
# ---------------------------------------------------------------------------

_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        # A value already set in the real environment wins, so a one-off
        # override on the command line still works.
        os.environ.setdefault(_key.strip(), _value.strip())


# ---------------------------------------------------------------------------
# SETUP -- change these for your own machine
# ---------------------------------------------------------------------------

# Your local MySQL login.
#
# Every machine has a different MySQL password, so these read from the
# environment first and fall back to the common defaults. To use your own,
# set them before starting -- or just edit the fallback values below.
#
#     set SKILLSCOPE_DB_PASSWORD=yourpassword
#
# The database is created automatically if it does not exist, so there is no
# CREATE DATABASE step.
DATABASE_NAME = os.environ.get("SKILLSCOPE_DB_NAME", "skillscope")
DATABASE_USER = os.environ.get("SKILLSCOPE_DB_USER", "root")
DATABASE_PASSWORD = os.environ.get("SKILLSCOPE_DB_PASSWORD", "")
DATABASE_HOST = os.environ.get("SKILLSCOPE_DB_HOST", "127.0.0.1")
DATABASE_PORT = os.environ.get("SKILLSCOPE_DB_PORT", "3306")

# PRODUCTION switches on everything a live, public deployment needs: DEBUG off,
# HTTPS-only cookies, compressed static files, uploads on Cloudinary, and
# refusing to start when a required value is missing.
#
# The Dockerfile sets SKILLSCOPE_PRODUCTION=1, so it applies both while the
# image is being built and while it runs. (Render's own RENDER=true is also
# honoured, for deploying without Docker.) On a laptop neither is set, and
# everything behaves exactly as before.
PRODUCTION = (os.environ.get("SKILLSCOPE_PRODUCTION") == "1"
              or os.environ.get("RENDER") == "true")

# Used to sign session cookies. Fine for local development; on Render it is
# generated for you (see render.yaml), and the app refuses to start without it.
SECRET_KEY = os.environ.get(
    "SKILLSCOPE_SECRET_KEY",
    "django-insecure-local-development-only-replace-before-deploying",
)
if PRODUCTION and (SECRET_KEY.startswith("django-insecure")
                   or "replace-with" in SECRET_KEY
                   or len(SECRET_KEY) < 40):
    # Also catches the placeholder from render.env.example being pasted in
    # unchanged -- it is public, so anyone could forge a login with it.
    raise RuntimeError(
        "Set SKILLSCOPE_SECRET_KEY to a long random value (40+ characters).")

# DEBUG on  -> Django shows a detailed traceback when something breaks.
#              Useful while building, alarming in front of an audience.
# DEBUG off -> the calm SkillScope error page is shown instead.
#
# Off by default in production, on by default on a laptop. Override either way:
#     set SKILLSCOPE_DEBUG=0     (Windows, before starting the server)
DEBUG = os.environ.get("SKILLSCOPE_DEBUG", "0" if PRODUCTION else "1") != "0"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "0.0.0.0", "testserver"]

# Render tells the app its own public address, e.g. skillscope.onrender.com.
# Without adding it here every request would be rejected with a 400.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

# Any extra domains, comma separated -- for instance a custom domain later.
ALLOWED_HOSTS += [h.strip() for h in os.environ.get("SKILLSCOPE_HOSTS", "").split(",") if h.strip()]

# Written into the QR code on every certificate, so a phone scanning it knows
# which server to ask. On Render this MUST be the public address -- if it
# stayed as localhost, every certificate would scan to nothing.
SITE_BASE_URL = os.environ.get(
    "SKILLSCOPE_SITE_URL",
    f"https://{RENDER_HOST}" if RENDER_HOST else "http://localhost:8000",
).rstrip("/")
if PRODUCTION and "localhost" in SITE_BASE_URL:
    # Refuse to start rather than print certificates whose QR codes lead
    # nowhere. Set SKILLSCOPE_SITE_URL to the site's public https:// address.
    raise RuntimeError(
        "SKILLSCOPE_SITE_URL is still localhost. Set it to the public address, "
        "e.g. https://skillscope.onrender.com")

# The site's own address is always an allowed host, whichever way it was given.
_site_host = SITE_BASE_URL.split("://", 1)[-1].split("/", 1)[0]
if _site_host and _site_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_site_host)

# Django refuses a form posted from an origin it has not been told to trust.
# Render serves over HTTPS, so without this, signing in would fail.
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS
                        if h not in ("localhost", "127.0.0.1", "[::1]", "0.0.0.0", "testserver")]

if PRODUCTION:
    # Render terminates HTTPS in front of the app and forwards plain HTTP.
    # This header is how Django learns the original request was secure.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ---------------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # SkillScope
    "accounts",
    "learning",
    "competency",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves our CSS, JavaScript and fonts efficiently in production. Must sit
    # directly after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

# On a laptop: MySQL, using the SKILLSCOPE_DB_* values above.
# On Render:   PostgreSQL. Render hands the app one DATABASE_URL containing
#              the host, name, user and password, and that takes priority.
#
# Nothing in SkillScope uses MySQL-only or Postgres-only SQL -- every query goes
# through Django -- so the same code runs unchanged on either.
if os.environ.get("DATABASE_URL"):
    import ssl

    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,          # reuse connections between requests
            conn_health_checks=True,   # but drop one that has gone stale
        )
    }

    # A hosted MySQL such as Aiven hands out a URL ending "?ssl-mode=REQUIRED".
    # That is a flag for MySQL's own command-line tools; PyMySQL, which we use,
    # rejects it outright ("unexpected keyword argument 'ssl-mode'") and the
    # site could never connect. So translate it into PyMySQL's own settings.
    _db = DATABASES["default"]
    if _db["ENGINE"] == "django.db.backends.mysql":
        _options = _db.setdefault("OPTIONS", {})
        _ssl_mode = str(_options.pop("ssl-mode", _options.pop("ssl_mode", ""))).upper()
        _options["charset"] = "utf8mb4"

        # Aiven signs its servers with its own certificate authority. With that
        # certificate present, the connection is encrypted AND the server's
        # identity is checked. It is a public certificate, not a secret.
        _ca = BASE_DIR / "config" / "db-ca.pem"
        if _ca.exists():
            _options["ssl"] = {"ca": str(_ca)}
        elif _ssl_mode in ("REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"):
            # No certificate supplied: still encrypted, but the server's
            # identity is not verified. Add config/db-ca.pem to close that gap.
            _options["ssl"] = {"check_hostname": False, "verify_mode": ssl.CERT_NONE}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": DATABASE_NAME,
            "USER": DATABASE_USER,
            "PASSWORD": DATABASE_PASSWORD,
            "HOST": DATABASE_HOST,
            "PORT": DATABASE_PORT,
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

# Tests run against an in-memory SQLite database instead of MySQL.
#
# Django builds a fresh database for every test run, and doing that in MySQL
# takes about eighteen minutes on a laptop -- long enough that nobody runs the
# tests at all. In memory it takes seconds. Nothing here uses MySQL-specific
# SQL, so the same code is exercised either way.
if "test" in sys.argv:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
    # Django deliberately makes password hashing slow, which is right for a
    # real login and wrong for a test suite that creates hundreds of accounts.
    # This applies ONLY while running tests -- real passwords are always
    # hashed with the strong default.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# AUTHENTICATION
#
# AUTH_USER_MODEL points Django at our own User class instead of its built-in
# one, which is how a user gets a role and an institution. This has to be set
# before the very first migration is run -- changing it afterwards means
# dropping the database and starting again.
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

# Sign-in uses the email address: User.USERNAME_FIELD is "email", so
# Django's standard authentication backend already does the right thing.

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# LOCALE
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# STATIC FILES (our CSS, bundled Bootstrap/Chart.js/qrcode.js, fonts)
# and MEDIA (files people upload: course material, logos, photos)
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Where static files and uploads are kept.
#
# Static (our CSS/JS/fonts): WhiteNoise compresses them and gives each a
# fingerprinted name, so browsers can cache them safely forever.
#
# Uploads: on disk in media/ by default. When CLOUDINARY_URL is set -- which it
# must be on Render, whose disk is wiped on every deploy -- they go to
# Cloudinary instead. See config/storage.py for why.
USE_CLOUDINARY = bool(os.environ.get("CLOUDINARY_URL"))

STORAGES = {
    "default": {
        "BACKEND": ("config.storage.CloudinaryStorage" if USE_CLOUDINARY
                    else "django.core.files.storage.FileSystemStorage"),
    },
    "staticfiles": {
        # Fingerprinted names need `collectstatic` to have run first, which
        # the Docker build does. Keyed to PRODUCTION rather than DEBUG on
        # purpose: demo mode on a laptop turns DEBUG off but never runs
        # collectstatic, and would otherwise fail on every page.
        "BACKEND": ("whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if PRODUCTION
                    else "django.contrib.staticfiles.storage.StaticFilesStorage"),
    },
}

if PRODUCTION and USE_CLOUDINARY and "API_KEY" in os.environ["CLOUDINARY_URL"]:
    # The placeholder from render.env.example, pasted in unchanged.
    raise RuntimeError(
        "CLOUDINARY_URL still contains the example placeholder. Paste the real "
        "value from your Cloudinary dashboard.")

if PRODUCTION and not USE_CLOUDINARY:
    # Refuse to start rather than quietly lose every upload on the next deploy.
    raise RuntimeError(
        "Set CLOUDINARY_URL before deploying. Without it, uploaded files are stored on "
        "a disk that Render wipes on every deploy.")

# Recorded lectures are large. Anything above this is streamed to a temporary
# file instead of being held in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Largest file a trainer may upload, checked in the upload form.
MAX_UPLOAD_SIZE_MB = 100

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Django labels an error message "error", but the CSS class for a red alert is
# "alert-danger". Without this mapping every error message renders unstyled --
# the text appears, but with no red box around it, so it reads as ordinary
# copy rather than as something that went wrong.
MESSAGE_TAGS = {message_constants.ERROR: "danger"}
