# config/settings/local.py
from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Readable query logs in development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "apps":   {"handlers": ["console"], "level": "DEBUG"},  # our apps log at DEBUG
        "celery": {"handlers": ["console"], "level": "DEBUG"},
    },
}