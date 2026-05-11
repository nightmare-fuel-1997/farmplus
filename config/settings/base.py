# config/settings/base.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env file from project root

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # farmpulse/

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # hard fail if missing — intentional

DEBUG = False  # NEVER True in base. Overridden in local.py.

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")

# --- Apps ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",   # Django Channels — Sprint 4
]

LOCAL_APPS = [
    "apps.devices",
    "apps.telemetry",
    "apps.realtime",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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
            ],
        },
    },
]

# ASGI — required for Django Channels (Sprint 4)
ASGI_APPLICATION = "config.asgi.application"

# --- Database (TimescaleDB = PostgreSQL under the hood) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     os.environ["POSTGRES_DB"],
        "USER":     os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST":     os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT":     os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# --- Redis (used for: Celery broker, Celery result backend,
#                       Channels layer, Pub/Sub) ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# --- Django Channels Layer ---
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# --- Celery ---
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {}  # Empty — Phase 11 will populate this
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
from celery.schedules import timedelta
CELERY_BEAT_SCHEDULE = {
    'consume-telemetry-stream': {
        'task': 'telemetry.consume_stream',
        'schedule': timedelta(seconds=2),  # poll every 2 seconds
    },
}
CELERY_RESULT_EXPIRES = 60  # seconds — auto-expire all task results
# --- Telemetry Pipeline Config ---
TELEMETRY_REDIS_STREAM_KEY = "telemetry:stream"
TELEMETRY_REDIS_CONSUMER_GROUP = "pipeline-workers"
TELEMETRY_CLOCK_DRIFT_THRESHOLD_MS = 5 * 60 * 1000   # 5 minutes
TELEMETRY_BUFFER_THRESHOLD_MS     = 15 * 60 * 1000   # 15 minutes

# --- Internationalization ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"          # Always UTC in backend. Frontend converts to local time.
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"