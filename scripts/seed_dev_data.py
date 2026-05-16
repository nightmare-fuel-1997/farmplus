import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.devices.models import Organization, Farm, Device

# ─── Data Definition ──────────────────────────────────────────────────────────

SEED_DATA = [
    {
        "org": {"slug": "org-sunrise", "name": "Sunrise Poultry Co."},
        "farms": [
            {
                "slug": "farm-01",
                "name": "Farm Alpha",
                "devices": [
                    {"slug": "gw-lora-001", "name": "LoRa Gateway 001", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity"], "firmware_version": "1.0.0"},
                    {"slug": "gw-lora-002", "name": "LoRa Gateway 002", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity", "lux"], "firmware_version": "1.0.1"},
                ],
            },
            {
                "slug": "farm-02",
                "name": "Farm Beta",
                "devices": [
                    {"slug": "gw-lora-003", "name": "LoRa Gateway 003", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity", "nh3"], "firmware_version": "1.0.1"},
                    {"slug": "gw-lora-004", "name": "LoRa Gateway 004", "status": "inactive",
                     "sensor_capabilities": ["temperature", "humidity"], "firmware_version": "1.0.0"},
                ],
            },
        ],
    },
    {
        "org": {"slug": "org-greenvalley", "name": "Green Valley Farms Ltd."},
        "farms": [
            {
                "slug": "farm-gv-01",
                "name": "North Greenhouse",
                "devices": [
                    {"slug": "gw-gv-001", "name": "GV North Gateway 001", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity", "lux"], "firmware_version": "1.1.0"},
                    {"slug": "gw-gv-002", "name": "GV North Gateway 002", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity", "lux", "nh3"], "firmware_version": "1.1.0"},
                ],
            },
            {
                "slug": "farm-gv-02",
                "name": "South Greenhouse",
                "devices": [
                    {"slug": "gw-gv-003", "name": "GV South Gateway 001", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity"], "firmware_version": "1.0.2"},
                ],
            },
            {
                "slug": "farm-gv-03",
                "name": "Open Field A",
                "devices": [
                    {"slug": "gw-gv-004", "name": "GV Field Gateway 001", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity", "lux"], "firmware_version": "1.1.0"},
                    {"slug": "gw-gv-005", "name": "GV Field Gateway 002", "status": "stolen",  # Phase 9
                     "sensor_capabilities": ["temperature", "humidity"], "firmware_version": "1.0.0"},
                ],
            },
        ],
    },
    {
        "org": {"slug": "org-tehranagri", "name": "Tehran Agri Systems"},
        "farms": [
            {
                "slug": "farm-ta-01",
                "name": "Pilot Farm East",
                "devices": [
                    {"slug": "gw-ta-001", "name": "TA East Gateway 001", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity", "nh3"], "firmware_version": "1.0.3"},
                    {"slug": "gw-ta-002", "name": "TA East Gateway 002", "status": "active",
                     "sensor_capabilities": ["temperature", "humidity"], "firmware_version": "1.0.3"},
                ],
            },
            {
                "slug": "farm-ta-02",
                "name": "Pilot Farm West",
                "devices": [
                    {"slug": "gw-ta-003", "name": "TA West Gateway 001", "status": "inactive",
                     "sensor_capabilities": ["temperature", "humidity", "lux"], "firmware_version": "0.9.5"},
                ],
            },
        ],
    },
]

# ─── Seeding Logic ────────────────────────────────────────────────────────────

total_orgs = total_farms = total_devices = 0

for entry in SEED_DATA:
    org, created = Organization.objects.get_or_create(
        slug=entry["org"]["slug"],
        defaults={"name": entry["org"]["name"]},
    )
    print(f"{'[CREATED]' if created else '[EXISTS] '} Organization: {org.slug}")
    if created:
        total_orgs += 1

    for farm_data in entry["farms"]:
        devices = farm_data.pop("devices")
        farm, created = Farm.objects.get_or_create(
            slug=farm_data["slug"],
            organization=org,
            defaults={"name": farm_data["name"]},
        )
        print(f"  {'[CREATED]' if created else '[EXISTS] '} Farm: {farm.slug}")
        if created:
            total_farms += 1

        for dev_data in devices:
            device, created = Device.objects.get_or_create(
                slug=dev_data["slug"],
                defaults={
                    "farm": farm,
                    "name": dev_data["name"],
                    "status": dev_data["status"],
                    "sensor_capabilities": dev_data["sensor_capabilities"],
                    "firmware_version": dev_data["firmware_version"],
                },
            )
            print(f"    {'[CREATED]' if created else '[EXISTS] '} Device: {device.slug} ({dev_data['status']})")
            if created:
                total_devices += 1

print(f"\n✅ Seed complete — {total_orgs} orgs, {total_farms} farms, {total_devices} devices added.")