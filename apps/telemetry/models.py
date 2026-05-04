# apps/telemetry/models.py
from django.db import models
from apps.devices.models import Device


class TelemetryReading(models.Model):
    """
    One row = one telemetry payload from one device.
    This table will be converted to a TimescaleDB hypertable
    partitioned by received_at (1-day chunks).

    DO NOT add a surrogate primary key — TimescaleDB hypertables
    work best without a single-column integer PK on time-series tables.
    """

    device      = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="readings")
    received_at = models.DateTimeField(db_index=True)       # server timestamp — partition key
    sent_ts     = models.BigIntegerField()                  # device timestamp (ms epoch)
    seq         = models.SmallIntegerField()                # 0–65535 sequence number
    is_buffered = models.BooleanField(default=False)
    clock_drift_ms = models.IntegerField(default=0)         # computed by pipeline Step 3

    # Sensor readings — temperature and humidity always present
    temperature = models.FloatField()
    humidity    = models.FloatField()

    # Optional sensors — NULL means device doesn't have this sensor
    lux         = models.FloatField(null=True, blank=True)
    nh3         = models.FloatField(null=True, blank=True)

    # Schema version that produced this reading — for future data archaeology
    schema_version = models.CharField(max_length=8, default="1.0")

    class Meta:
        # Composite index: most queries are "give me readings for device X in time range Y"
        indexes = [
            models.Index(fields=["device", "received_at"]),
        ]
        # No unique_together — duplicate rows can happen during buffered replay
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.device} @ {self.received_at}"