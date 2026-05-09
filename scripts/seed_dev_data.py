# scripts/seed_dev_data.py
import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.devices.models import Organization, Farm, Device

org, created = Organization.objects.get_or_create(
    slug="org_sunrise",
    defaults={"name": "Sunrise Poultry Co."}
)
print(f"{'Created' if created else 'Exists'}: Organization → {org.slug}")

farm, created = Farm.objects.get_or_create(
    slug="farm_01",
    organization=org,
    defaults={"name": "Farm Alpha"}
)
print(f"{'Created' if created else 'Exists'}: Farm → {farm.slug}")

device, created = Device.objects.get_or_create(
    slug="gw_lora_001",
    defaults={"farm": farm, "name": "LoRa Gateway 001", "status": "active"}
)
print(f"{'Created' if created else 'Exists'}: Device → {device.slug}")

print("\n✅ Seed data ready.")