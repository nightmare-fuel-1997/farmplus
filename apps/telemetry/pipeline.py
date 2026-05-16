# apps/telemetry/pipeline.py
import json
import logging
from datetime import datetime, timezone

from jsonschema import validate, ValidationError
from django.dispatch import Signal
from django.utils import timezone as dj_timezone

from .schemas import get_schema

logger = logging.getLogger(__name__)

CLOCK_DRIFT_WARN_MS = 5  * 60 * 1000
BUFFERED_CUTOFF_MS  = 15 * 60 * 1000

notification_candidate = Signal()


def run_pipeline(msg_id: str, fields: dict, redis_client) -> None:
    raw_payload = fields.get('payload', '{}')
    received_ts = int(fields.get('received_ts', 0))

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"[{msg_id}] Unparseable JSON: {e}")

    # STEP 1 — Schema Validation
    _validate_schema(msg_id, payload)
    logger.info(f"[{msg_id}] ✓ Step 1 | schema v{payload['schema_version']}")

    # STEP 2 — Device Identity & Auth
    device = _verify_device(msg_id, payload)
    logger.info(f"[{msg_id}] ✓ Step 2 | device={device.slug}")

    # STEP 3 — Clock Drift Check
    clock_drift_ms, is_old_buffered = _check_clock_drift(msg_id, payload, received_ts)
    logger.info(f"[{msg_id}] ✓ Step 3 | drift={clock_drift_ms:+,}ms | old_buffered={is_old_buffered}")

    # STEP 4 — Routing Fork
    is_buffered_path = _routing_fork(
        msg_id, payload, device, is_old_buffered, received_ts, redis_client
    )
    logger.info(f"[{msg_id}] ✓ Step 4 | path={'BUFFERED' if is_buffered_path else 'LIVE'}")

    # STEP 5 — TimescaleDB Write (always runs)
    _write_to_db(msg_id, payload, device, received_ts, clock_drift_ms)
    logger.info(f"[{msg_id}] ✓ Step 5 | written to TimescaleDB")


def write_to_db(msg_id, payload, device, received_ts, clock_drift_ms):
    from apps.telemetry.models import TelemetryReading
    readings = payload["readings"]

    received_at = datetime.fromtimestamp(received_ts / 1000.0, tz=timezone.utc)

    # Guard: clamp sent_ts to a valid positive range
    # Protects against malformed buffer files with bad timestamps
    sent_ts = payload["sent_ts"]
    MAX_BIGINT = 9_223_372_036_854_775_807
    if not (0 < sent_ts <= MAX_BIGINT):
        logger.warning(f"{msg_id} Invalid sent_ts={sent_ts}, substituting received_ts")
        sent_ts = received_ts

    TelemetryReading.objects.create(
        device=device,
        received_at=received_at,
        sent_ts=sent_ts,
        seq=payload["seq"],
        is_buffered=payload.get("is_buffered", False),
        clock_drift_ms=clock_drift_ms,
        temperature=readings["temperature"],
        humidity=readings["humidity"],
        lux=readings.get("lux"),
        nh3=readings.get("nh3"),
        schema_version=payload["schema_version"],
    )


def _routing_fork(msg_id, payload, device, is_old_buffered, received_ts, redis_client):
    is_buffered = payload.get('is_buffered', False) or is_old_buffered
    if is_buffered:
        logger.info(f"[{msg_id}] ↷ Buffered path | skipping Pub/Sub and alerts")
        return True

    farm_id = payload['farm_id']
    pubsub_channel = f"farm:{farm_id}:live"
    message = json.dumps({
        "device_id":      payload['device_id'],
        "farm_id":        farm_id,
        "org_id":         payload['org_id'],
        "sent_ts":        payload['sent_ts'],
        "received_ts":    received_ts,
        "is_buffered":    False,
        "readings":       payload['readings'],
        "schema_version": payload['schema_version'],
    })
    redis_client.publish(pubsub_channel, message)
    logger.info(f"[{msg_id}] → Published to Pub/Sub '{pubsub_channel}'")
    notification_candidate.send(sender=None, payload=payload, device=device, msg_id=msg_id)
    return False


def _check_clock_drift(msg_id, payload, received_ts):
    sent_ts = payload['sent_ts']
    clock_drift_ms = received_ts - sent_ts
    if abs(clock_drift_ms) > CLOCK_DRIFT_WARN_MS:
        logger.warning(
            f"[{msg_id}] ⚠ Clock drift | "
            f"drift={clock_drift_ms:+,}ms ({clock_drift_ms/1000/60:.1f} min) | "
            f"device={payload['device_id']}"
        )
    is_old_buffered = clock_drift_ms > BUFFERED_CUTOFF_MS
    return clock_drift_ms, is_old_buffered


def _validate_schema(msg_id, payload):
    version = payload.get('schema_version')
    if not version:
        raise ValueError(f"[{msg_id}] Missing 'schema_version'")
    try:
        schema = get_schema(version)
    except ValueError:
        raise ValueError(f"[{msg_id}] Unknown schema_version '{version}'")
    try:
        validate(instance=payload, schema=schema)
    except ValidationError as e:
        field_path = ' -> '.join(str(p) for p in e.absolute_path) or 'root'
        raise ValueError(f"[{msg_id}] Schema validation failed at '{field_path}': {e.message}")


def _verify_device(msg_id, payload):
    from apps.devices.models import Device
    device_id = payload['device_id']
    farm_id   = payload['farm_id']
    org_id    = payload['org_id']
    try:
        device = Device.objects.select_related('farm__organization').get(slug=device_id)
    except Device.DoesNotExist:
        raise ValueError(f"[{msg_id}] Auth failed — unknown device '{device_id}'")
    if device.status != Device.Status.ACTIVE:
        raise ValueError(f"[{msg_id}] Auth failed — device '{device_id}' is '{device.status}'")
    if device.farm.slug != farm_id:
        raise ValueError(f"[{msg_id}] Auth failed — farm mismatch (possible spoofing)")
    if device.farm.organization.slug != org_id:
        raise ValueError(f"[{msg_id}] Auth failed — org mismatch (possible spoofing)")
    return device