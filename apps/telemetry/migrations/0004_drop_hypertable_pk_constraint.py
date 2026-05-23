from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("telemetry", "0003_alter_telemetryreading_options"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE telemetry_telemetryreading DROP CONSTRAINT IF EXISTS telemetry_telemetryreading_pkey CASCADE;",
            reverse_sql="ALTER TABLE telemetry_telemetryreading ADD CONSTRAINT telemetry_telemetryreading_pkey PRIMARY KEY (received_at);",
        )
    ]
