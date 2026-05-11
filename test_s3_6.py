# test_s3_6.py
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import time
import redis
from django.conf import settings
from apps.telemetry.pipeline import run_pipeline
from apps.telemetry.models import TelemetryReading

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

now_ms = int(time.time() * 1000)

fields = {
    'payload': '{"schema_version":"1.0","org_id":"org-sunrise","farm_id":"farm01",'
               '"device_id":"gw-lora-001","sent_ts":' + str(now_ms - 2000) + ','
               '"seq":99,"is_buffered":false,'
               '"readings":{"temperature":24.3,"humidity":61.2,"lux":430.0,"nh3":13.2}}',
    'topic':       'org-sunrise/farms/farm01/gateways/gw-lora-001/telemetry',
    'received_ts': str(now_ms),
}

count_before = TelemetryReading.objects.count()
run_pipeline("test-s3-6-001", fields, r)
count_after = TelemetryReading.objects.count()

print(f"Rows before: {count_before}")
print(f"Rows after:  {count_after}")
print(f"✓ Inserted:  {count_after - count_before} row")

# Read it back
reading = TelemetryReading.objects.order_by('-received_at').first()
print(f"✓ device={reading.device.slug} | temp={reading.temperature} | nh3={reading.nh3} | buffered={reading.is_buffered}")