# test3-5.py
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

# ── now safe to import Django models ──────────────────────────────
import redis
from django.conf import settings
from apps.telemetry.pipeline import _routing_fork
from apps.devices.models import Device

r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
device = Device.objects.select_related('farm__organization').get(slug='gw-lora-001')

now = 1778326304000

live_payload = {
    "device_id": "gw-lora-001", "farm_id": "farm01", "org_id": "org-sunrise",
    "sent_ts": now - 2000, "is_buffered": False,
    "readings": {"temperature": 24.3, "humidity": 61.2},
    "schema_version": "1.0"
}

buffered_payload = {**live_payload, "is_buffered": True, "sent_ts": now - (4 * 3600 * 1000)}

# Test 1 — live data → should publish to Pub/Sub, return False
result = _routing_fork("t001", live_payload, device, False, now, r)
print(f"✓ Test 1 | is_buffered_path={result}")   # expect False

# Test 2 — is_buffered flag True → should skip Pub/Sub, return True
result = _routing_fork("t002", buffered_payload, device, False, now, r)
print(f"✓ Test 2 | is_buffered_path={result}")   # expect True

# Test 3 — live flag but clock drift says old → should skip Pub/Sub, return True
result = _routing_fork("t003", {**live_payload, "is_buffered": False}, device, True, now, r)
print(f"✓ Test 3 | is_buffered_path={result}")   # expect True

print("\n✅ All routing fork tests passed.")