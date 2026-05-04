# apps/devices/models.py
import uuid
from django.db import models


class Organization(models.Model):
    """
    Top-level tenant. In Phase 12, each org is isolated.
    Using slug as the primary lookup key (matches org_id in MQTT payload).
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug       = models.SlugField(max_length=64, unique=True)  # e.g. "org_sunrise"
    name       = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.slug


class Farm(models.Model):
    """
    A physical farm belonging to an organization.
    slug matches farm_id in the MQTT payload.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="farms")
    slug         = models.SlugField(max_length=64)        # e.g. "farm_01"
    name         = models.CharField(max_length=255)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "slug")        # farm_01 must be unique per org

    def __str__(self):
        return f"{self.organization.slug}/{self.slug}"


class Device(models.Model):
    """
    A physical LoRa gateway registered in the system.
    slug matches device_id in the MQTT payload.
    """

    class Status(models.TextChoices):
        ACTIVE   = "active",   "Active"
        INACTIVE = "inactive", "Inactive"
        STOLEN   = "stolen",   "Stolen"   # Phase 9: stolen device handling

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm                = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="devices")
    slug                = models.SlugField(max_length=64)         # e.g. "gw_lora_001"
    name                = models.CharField(max_length=255)
    status              = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    sensor_capabilities = models.JSONField(default=list)          # e.g. ["temperature", "humidity", "nh3"]
    firmware_version    = models.CharField(max_length=32, blank=True, default="")
    last_seen_at        = models.DateTimeField(null=True, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("farm", "slug")                        # device slug unique per farm

    def __str__(self):
        return f"{self.farm}/{self.slug}"