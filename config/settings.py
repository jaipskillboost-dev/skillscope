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

# Used to sign session cookies. Fine for local development; replace it with a
# long random value before putting this on a public server.
SECRET_KEY = os.environ.get(
    "SKILLSCOPE_SECRET_KEY",
    "django-insecure-local-development-only-replace-before-deploying",
)

# Shows a detailed error page when something breaks. Turn off in production.
# DEBUG on  -> Django shows a detailed traceback when something breaks.
#              Useful while building, alarming in front of an audience.
# DEBUG off -> the calm SkillScope error page is shown instead.
#
# Set it with the environment variable rather than editing this line, so the
# demo and development use the same file:
#     set SKILLSCOPE_DEBUG=0     (Windows, before starting the server)
DEBUG = os.environ.get("SKILLSCOPE_DEBUG", "1") != "0"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "0.0.0.0", "testserver"]

# Written into the QR code on every certificate, so a phone scanning it knows
# which server to ask.
SITE_BASE_URL = "http://localhost:8000"


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
