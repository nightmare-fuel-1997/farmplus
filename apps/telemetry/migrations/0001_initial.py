# apps/telemetry/migrations/0001_initial.py
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("devices", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelemetryReading",
            fields=[
                ("received_at", models.DateTimeField(primary_key=True, serialize=False)),
                ("sent_ts",        models.BigIntegerField()),
                ("seq",            models.SmallIntegerField()),
                ("is_buffered",    models.BooleanField(default=False)),
                ("clock_drift_ms", models.IntegerField(default=0)),
                ("temperature",    models.FloatField()),
                ("humidity",       models.FloatField()),
                ("lux",            models.FloatField(blank=True, null=True)),
                ("nh3",            models.FloatField(blank=True, null=True)),
                ("schema_version", models.CharField(default="1.0", max_length=8)),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="readings",
                        to="devices.device",
                    ),
                ),
            ],
            options={
                "ordering": ["-received_at"],
                "indexes": [
                    models.Index(
                        fields=["device", "received_at"],
                        name="telemetry_t_device__3541f6_idx",
                    )
                ],
            },
        ),
    ]