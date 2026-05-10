# test_s3_3.py
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.telemetry.pipeline import _verify_device

base = {
    "device_id": "gw-lora-001",
    "farm_id":   "farm01",
    "org_id":    "org-sunrise",
}

device = _verify_device("t001", base)
print(f"✓ Test 1 passed | device={device.slug} | farm={device.farm.slug} | org={device.farm.organization.slug}")

try:
    _verify_device("t002", {**base, "device_id": "ghost-device-999"})
except ValueError as e:
    print(f"✓ Test 2 rejected: {e}")

try:
    _verify_device("t003", {**base, "farm_id": "farm-attacker-01"})
except ValueError as e:
    print(f"✓ Test 3 rejected: {e}")

try:
    _verify_device("t004", {**base, "org_id": "org-evil"})
except ValueError as e:
    print(f"✓ Test 4 rejected: {e}")