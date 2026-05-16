# apps/devices/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from typing import List
from datetime import datetime
from ninja import Schema
from .models import Organization, Farm, Device

devices_router = Router()
farms_router   = Router()


# ── Schemas ──────────────────────────────────────────────────────────────────

class FarmOut(Schema):
    slug: str
    name: str
    organization_slug: str
    created_at: datetime

    @staticmethod
    def resolve_organization_slug(obj):
        return obj.organization.slug


class DeviceOut(Schema):
    slug: str
    name: str
    status: str
    firmware_version: str
    sensor_capabilities: list
    last_seen_at: datetime | None
    farm_slug: str
    created_at: datetime

    @staticmethod
    def resolve_farm_slug(obj):
        return obj.farm.slug


# ── Device Endpoints ──────────────────────────────────────────────────────────

@devices_router.get("/", response=List[DeviceOut], summary="List all devices")
def list_devices(request):
    return Device.objects.select_related("farm__organization").all()


@devices_router.get("/{device_slug}/", response=DeviceOut, summary="Get a single device")
def get_device(request, device_slug: str):
    return get_object_or_404(
        Device.objects.select_related("farm__organization"),
        slug=device_slug
    )


# ── Farm Endpoints ────────────────────────────────────────────────────────────

@farms_router.get("/", response=List[FarmOut], summary="List all farms")
def list_farms(request):
    return Farm.objects.select_related("organization").all()


@farms_router.get("/{farm_slug}/", response=FarmOut, summary="Get a single farm")
def get_farm(request, farm_slug: str):
    return get_object_or_404(
        Farm.objects.select_related("organization"),
        slug=farm_slug
    )


@farms_router.get(
    "/{farm_slug}/devices/",
    response=List[DeviceOut],
    summary="List all devices on a farm"
)
def list_farm_devices(request, farm_slug: str):
    farm = get_object_or_404(Farm, slug=farm_slug)
    return Device.objects.select_related("farm__organization").filter(farm=farm)