from django.contrib import admin
from .models import TelemetryReading

@admin.register(TelemetryReading)
class TelemetryReadingAdmin(admin.ModelAdmin):
    list_display  = ["device", "received_at", "temperature", "humidity", "lux", "nh3", "is_buffered"]
    list_filter   = ["is_buffered", "schema_version"]
    readonly_fields = ["received_at", "sent_ts", "clock_drift_ms"]