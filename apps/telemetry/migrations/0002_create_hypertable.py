from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("telemetry", "0001_initial"),   # runs after the table is created
    ]

    operations = [
        migrations.RunSQL(
            # --- FORWARD: activate TimescaleDB and convert to hypertable ---
            sql=[
                # Enable the TimescaleDB extension (idempotent)
                "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;",

                # Convert the table to a hypertable partitioned by received_at
                # chunk_time_interval = 1 day (86400 seconds)
                """
                SELECT create_hypertable(
                    'telemetry_telemetryreading',
                    'received_at',
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE
                );
                """,

                # Composite index for the most common query pattern:
                # "all readings for device X between time A and B"
                """
                CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
                ON telemetry_telemetryreading (device_id, received_at DESC);
                """,
            ],
            # --- REVERSE: drop extension (only for clean dev resets) ---
            reverse_sql=[
                "DROP EXTENSION IF EXISTS timescaledb CASCADE;",
            ],
        ),
    ]