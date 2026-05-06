# apps/telemetry/models.py
from django.db import models
from apps.devices.models import Device


class TelemetryReading(models.Model):

    device         = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="readings")
    received_at    = models.DateTimeField()
    sent_ts        = models.BigIntegerField()
    seq            = models.SmallIntegerField()
    is_buffered    = models.BooleanField(default=False)
    clock_drift_ms = models.IntegerField(default=0)
    temperature    = models.FloatField()
    humidity       = models.FloatField()
    lux            = models.FloatField(null=True, blank=True)
    nh3            = models.FloatField(null=True, blank=True)
    schema_version = models.CharField(max_length=8, default="1.0")

    class Meta:
        indexes = [
            models.Index(fields=["device", "received_at"]),
        ]
        ordering  = ["-received_at"]

    def __str__(self):
        return f"{self.device} @ {self.received_at}"