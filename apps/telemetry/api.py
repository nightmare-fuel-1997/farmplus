from ninja import Router, Query
from django.shortcuts import get_object_or_404
from typing import List
from datetime import datetime
from ninja import Schema

from .models import TelemetryReading
from apps.devices.models import Farm, Device

router = Router()


# ── Schemas ──────────────────────────────────────────────────────────────────

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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/farms/{farm_slug}/latest/",
    response=List[TelemetryOut],
    summary="Latest reading per device on a farm"
)
def latest_per_farm(request, farm_slug: str):
    farm = get_object_or_404(Farm, slug=farm_slug)
    devices = Device.objects.filter(farm=farm)

    # Get the single latest reading for each device
    readings = []
    for device in devices:
        reading = (
            TelemetryReading.objects
            .filter(device=device)
            .order_by("-received_at")
            .first()
        )
        if reading:
            readings.append(reading)
    return readings


@router.get(
    "/farms/{farm_slug}/history/",
    response=List[TelemetryOut],
    summary="Historical readings for a farm (paginated)"
)
def farm_history(
    request,
    farm_slug: str,
    limit:  int = Query(50, ge=1, le=500),
    offset: int = Query(0,  ge=0),
):
    farm = get_object_or_404(Farm, slug=farm_slug)
    devices = Device.objects.filter(farm=farm)
    return (
        TelemetryReading.objects
        .filter(device__in=devices)
        .select_related("device")
        .order_by("-received_at")[offset : offset + limit]
    )


@router.get(
    "/devices/{device_slug}/latest/",
    response=TelemetryOut,
    summary="Latest reading for a specific device"
)
def device_latest(request, device_slug: str):
    device = get_object_or_404(Device, slug=device_slug)
    reading = (
        TelemetryReading.objects
        .filter(device=device)
        .order_by("-received_at")
        .first()
    )
    if not reading:
        from ninja.errors import HttpError
        raise HttpError(404, f"No readings found for device '{device_slug}'")
    return reading


@router.get(
    "/devices/{device_slug}/history/",
    response=List[TelemetryOut],
    summary="Historical readings for a specific device (paginated)"
)
def device_history(
    request,
    device_slug: str,
    limit:  int = Query(50, ge=1, le=500),
    offset: int = Query(0,  ge=0),
):
    device = get_object_or_404(Device, slug=device_slug)
    return (
        TelemetryReading.objects
        .filter(device=device)
        .order_by("-received_at")[offset : offset + limit]
    )