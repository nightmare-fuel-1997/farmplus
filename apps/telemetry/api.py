# apps/telemetry/api.py
from ninja import Router, Query
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError
from typing import List
from datetime import datetime
from ninja import Schema
from .models import TelemetryReading
from apps.devices.models import Organization, Farm, Device

router = Router()

# ─── Schema ───────────────────────────────────────────────────────────────────

class TelemetryOut(Schema):
    received_at: datetime
    sent_ts: int
    seq: int
    is_buffered: bool
    clock_drift_ms: int
    temperature: float
    humidity: float
    lux: float | None
    nh3: float | None
    schema_version: str
    device_slug: str

    @staticmethod
    def resolve_device_slug(obj):
        return obj.device.slug

# ─── Helper ───────────────────────────────────────────────────────────────────

def _history_qs(devices_qs, limit, offset, from_dt, to_dt):
    qs = TelemetryReading.objects.filter(
        device__in=devices_qs
    ).select_related("device").order_by("-received_at")
    if from_dt:
        qs = qs.filter(received_at__gte=from_dt)
    if to_dt:
        qs = qs.filter(received_at__lte=to_dt)
    return qs[offset: offset + limit]

# ─── Org-level Telemetry ──────────────────────────────────────────────────────

@router.get("/orgs/{org_slug}/latest", response=List[TelemetryOut],
            summary="Latest reading per device across an entire org")
def org_latest(request, org_slug: str):
    org = get_object_or_404(Organization, slug=org_slug)
    devices = Device.objects.filter(farm__organization=org)
    readings = []
    for device in devices:
        r = TelemetryReading.objects.filter(device=device).order_by("-received_at").first()
        if r:
            readings.append(r)
    return readings

@router.get("/orgs/{org_slug}/history", response=List[TelemetryOut],
            summary="Historical readings for an entire org (paginated)")
def org_history(
    request, org_slug: str,
    limit:   int      = Query(50, ge=1, le=500),
    offset:  int      = Query(0, ge=0),
    from_dt: datetime = Query(None),
    to_dt:   datetime = Query(None),
):
    org = get_object_or_404(Organization, slug=org_slug)
    devices = Device.objects.filter(farm__organization=org)
    return _history_qs(devices, limit, offset, from_dt, to_dt)

# ─── Farm-level Telemetry ─────────────────────────────────────────────────────

@router.get("/farms/{farm_slug}/latest", response=List[TelemetryOut],
            summary="Latest reading per device on a farm")
def farm_latest(request, farm_slug: str):
    farm = get_object_or_404(Farm, slug=farm_slug)
    devices = Device.objects.filter(farm=farm)
    readings = []
    for device in devices:
        r = TelemetryReading.objects.filter(device=device).order_by("-received_at").first()
        if r:
            readings.append(r)
    return readings

@router.get("/farms/{farm_slug}/history", response=List[TelemetryOut],
            summary="Historical readings for a farm (paginated, filterable)")
def farm_history(
    request, farm_slug: str,
    limit:   int      = Query(50, ge=1, le=500),
    offset:  int      = Query(0, ge=0),
    from_dt: datetime = Query(None),
    to_dt:   datetime = Query(None),
):
    farm = get_object_or_404(Farm, slug=farm_slug)
    devices = Device.objects.filter(farm=farm)
    return _history_qs(devices, limit, offset, from_dt, to_dt)

# ─── Device-level Telemetry ───────────────────────────────────────────────────

@router.get("/devices/{device_slug}/latest", response=TelemetryOut,
            summary="Latest reading for a specific device")
def device_latest(request, device_slug: str):
    device = get_object_or_404(Device, slug=device_slug)
    reading = TelemetryReading.objects.filter(device=device).order_by("-received_at").first()
    if not reading:
        raise HttpError(404, f"No readings found for device '{device_slug}'")
    return reading

@router.get("/devices/{device_slug}/history", response=List[TelemetryOut],
            summary="Historical readings for a specific device (paginated, filterable)")
def device_history(
    request, device_slug: str,
    limit:   int      = Query(50, ge=1, le=500),
    offset:  int      = Query(0, ge=0),
    from_dt: datetime = Query(None),
    to_dt:   datetime = Query(None),
):
    device = get_object_or_404(Device, slug=device_slug)
    return _history_qs(Device.objects.filter(pk=device.pk), limit, offset, from_dt, to_dt)