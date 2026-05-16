# scripts/seed_dev_data.py
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.devices.models import Organization, Farm, Device


SEED_DATA = [
    {
        "slug": "org-sunrise",
        "name": "Sunrise Poultry Co.",
        "farms": [
            {
                "slug": "farm01",
                "name": "Farm Alpha",
                "devices": [
                    {
                        "slug": "gw-lora-001",
                        "name": "LoRa Gateway 001",
                        "status": "active",
                        "firmware_version": "1.0.0",
                        "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"],
                    },
                    {
                        "slug": "gw-lora-002",
                        "name": "LoRa Gateway 002",
                        "status": "active",
                        "firmware_version": "1.0.1",
                        "sensor_capabilities": ["temperature", "humidity", "lux"],
                    },
                    {
                        "slug": "gw-lora-003",
                        "name": "LoRa Gateway 003",
                        "status": "inactive",
                        "firmware_version": "1.0.0",
                        "sensor_capabilities": ["temperature", "humidity"],
                    },
                ],
            },
            {
                "slug": "farm02",
                "name": "Farm Beta",
                "devices": [
                    {
                        "slug": "gw-lora-004",
                        "name": "LoRa Gateway 004",
                        "status": "active",
                        "firmware_version": "1.1.0",
                        "sensor_capabilities": ["temperature", "humidity", "nh3"],
                    },
                    {
                        "slug": "gw-lora-005",
                        "name": "LoRa Gateway 005",
                        "status": "active",
                        "firmware_version": "1.1.0",
                        "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"],
                    },
                    {
                        "slug": "gw-lora-006",
                        "name": "LoRa Gateway 006",
                        "status": "inactive",
                        "firmware_version": "1.0.2",
                        "sensor_capabilities": ["temperature", "humidity"],
                    },
                ],
            },
        ],
    },
    {
        "slug": "org-greenfield",
        "name": "Greenfield Layers Ltd.",
        "farms": [
            {
                "slug": "farm10",
                "name": "Green Farm North",
                "devices": [
                    {
                        "slug": "gw-lora-101",
                        "name": "LoRa Gateway 101",
                        "status": "active",
                        "firmware_version": "1.0.0",
                        "sensor_capabilities": ["temperature", "humidity", "lux"],
                    },
                    {
                        "slug": "gw-lora-102",
                        "name": "LoRa Gateway 102",
                        "status": "active",
                        "firmware_version": "1.0.3",
                        "sensor_capabilities": ["temperature", "humidity", "nh3"],
                    },
                    {
                        "slug": "gw-lora-103",
                        "name": "LoRa Gateway 103",
                        "status": "active",
                        "firmware_version": "1.1.0",
                        "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"],
                    },
                ],
            },
            {
                "slug": "farm11",
                "name": "Green Farm South",
                "devices": [
                    {
                        "slug": "gw-lora-111",
                        "name": "LoRa Gateway 111",
                        "status": "active",
                        "firmware_version": "1.0.0",
                        "sensor_capabilities": ["temperature", "humidity"],
                    },
                    {
                        "slug": "gw-lora-112",
                        "name": "LoRa Gateway 112",
                        "status": "inactive",
                        "firmware_version": "1.0.1",
                        "sensor_capabilities": ["temperature", "humidity", "lux"],
                    },
                    {
                        "slug": "gw-lora-113",
                        "name": "LoRa Gateway 113",
                        "status": "active",
                        "firmware_version": "1.1.1",
                        "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"],
                    },
                ],
            },
        ],
    },
    {
        "slug": "org-northbarn",
        "name": "NorthBarn AgriSystems",
        "farms": [
            {
                "slug": "farm20",
                "name": "NorthBarn East",
                "devices": [
                    {
                        "slug": "gw-lora-201",
                        "name": "LoRa Gateway 201",
                        "status": "active",
                        "firmware_version": "1.0.4",
                        "sensor_capabilities": ["temperature", "humidity", "lux"],
                    },
                    {
                        "slug": "gw-lora-202",
                        "name": "LoRa Gateway 202",
                        "status": "active",
                        "firmware_version": "1.0.4",
                        "sensor_capabilities": ["temperature", "humidity", "nh3"],
                    },
                    {
                        "slug": "gw-lora-203",
                        "name": "LoRa Gateway 203",
                        "status": "active",
                        "firmware_version": "1.1.0",
                        "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"],
                    },
                ],
            },
            {
                "slug": "farm21",
                "name": "NorthBarn West",
                "devices": [
                    {
                        "slug": "gw-lora-211",
                        "name": "LoRa Gateway 211",
                        "status": "active",
                        "firmware_version": "1.0.2",
                        "sensor_capabilities": ["temperature", "humidity"],
                    },
                    {
                        "slug": "gw-lora-212",
                        "name": "LoRa Gateway 212",
                        "status": "inactive",
                        "firmware_version": "1.0.2",
                        "sensor_capabilities": ["temperature", "humidity", "lux"],
                    },
                    {
                        "slug": "gw-lora-213",
                        "name": "LoRa Gateway 213",
                        "status": "active",
                        "firmware_version": "1.1.2",
                        "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"],
                    },
                ],
            },
        ],
    },
]


def seed():
    org_count = farm_count = device_count = 0

    for org_data in SEED_DATA:
        org, created = Organization.objects.get_or_create(
            slug=org_data["slug"],
            defaults={"name": org_data["name"]},
        )
        if not created and org.name != org_data["name"]:
            org.name = org_data["name"]
            org.save(update_fields=["name"])
        org_count += 1
        print(f"{'Created' if created else 'Exists '} Organization → {org.slug}")

        for farm_data in org_data["farms"]:
            farm, created = Farm.objects.get_or_create(
                slug=farm_data["slug"],
                organization=org,
                defaults={"name": farm_data["name"]},
            )
            if not created and farm.name != farm_data["name"]:
                farm.name = farm_data["name"]
                farm.save(update_fields=["name"])
            farm_count += 1
            print(f"{'Created' if created else 'Exists '} Farm         → {farm.slug} ({org.slug})")

            for device_data in farm_data["devices"]:
                device, created = Device.objects.get_or_create(
                    slug=device_data["slug"],
                    defaults={
                        "farm": farm,
                        "name": device_data["name"],
                        "status": device_data["status"],
                        "firmware_version": device_data["firmware_version"],
                        "sensor_capabilities": device_data["sensor_capabilities"],
                    },
                )

                updated = False
                if device.farm_id != farm.id:
                    device.farm = farm
                    updated = True
                if device.name != device_data["name"]:
                    device.name = device_data["name"]
                    updated = True
                if device.status != device_data["status"]:
                    device.status = device_data["status"]
                    updated = True
                if device.firmware_version != device_data["firmware_version"]:
                    device.firmware_version = device_data["firmware_version"]
                    updated = True
                if device.sensor_capabilities != device_data["sensor_capabilities"]:
                    device.sensor_capabilities = device_data["sensor_capabilities"]
                    updated = True

                if updated:
                    device.save()

                device_count += 1
                label = "Created" if created else ("Updated" if updated else "Exists ")
                print(f"{label} Device       → {device.slug} ({farm.slug})")

    print("\n✅ Seed data ready.")
    print(f"Organizations: {org_count}")
    print(f"Farms:         {farm_count}")
    print(f"Devices:       {device_count}")


if __name__ == "__main__":
    seed()