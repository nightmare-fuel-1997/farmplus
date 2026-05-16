import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# ← Add this line — fixes the Windows prefork pool bug
os.environ.setdefault("FORKED_BY_MULTIPROCESSING", "1")

app = Celery("farmpulse")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()