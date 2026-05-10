# apps/telemetry/pipeline.py
import json
import time
import logging
from jsonschema import validate, ValidationError

from .schemas import get_schema

logger = logging.getLogger(__name__)

# Thresholds (in milliseconds)
CLOCK_DRIFT_WARN_MS   = 5  * 60 * 1000   # 5 minutes
BUFFERED_CUTOFF_MS    = 15 * 60 * 1000   # 15 minutes


def run_pipeline(msg_id: str, fields: dict, redis_client) -> None:
    """
    Assembly line. Each step raises an exception on failure.
    tasks.py catches exceptions and skips XACK — message stays in PEL.
    """
    # --- Parse raw stream fields ---
    raw_payload = fields.get('payload', '{}')
    received_ts = int(fields.get('received_ts', 0))

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"[{msg_id}] Unparseable JSON: {e}")

    # ----------------------------------------------------------------
    # STEP 1 — JSON Schema Validation
    # ----------------------------------------------------------------
    _validate_schema(msg_id, payload)
    logger.info(f"[{msg_id}] ✓ Step 1 passed | schema v{payload['schema_version']}")

    # ----------------------------------------------------------------
    # STEP 2 — Device Identity & Auth
    # ----------------------------------------------------------------
    device = _verify_device(msg_id, payload)
    logger.info(f"[{msg_id}] ✓ Step 2 passed | device={device.slug}")

    # ----------------------------------------------------------------
    # STEP 3 — Clock Drift Check
    # ----------------------------------------------------------------
    clock_drift_ms, is_old_buffered = _check_clock_drift(msg_id, payload, received_ts)
    logger.info(
        f"[{msg_id}] ✓ Step 3 passed | "
        f"drift={clock_drift_ms:+,}ms | "
        f"old_buffered={is_old_buffered}"
    )

    # ----------------------------------------------------------------
    # STEP 4 — Routing Fork                (S3-5, next)
    # STEP 5 — TimescaleDB Write           (S3-6)
    # ----------------------------------------------------------------


def _check_clock_drift(msg_id: str, payload: dict, received_ts: int) -> tuple[int, bool]:
    """
    Compare device sent_ts against server received_ts.

    Returns:
        clock_drift_ms  — signed integer (positive = message arrived late,
                          negative = device clock is ahead of server)
        is_old_buffered — True if sent_ts is older than BUFFERED_CUTOFF_MS
                          Used by the routing fork (S3-5) to skip live dashboard

    Never raises — clock drift is a warning, not a rejection.
    """
    sent_ts = payload['sent_ts']  # ms epoch from device RTC
    clock_drift_ms = received_ts - sent_ts

    # Warn if device clock is significantly off in either direction
    if abs(clock_drift_ms) > CLOCK_DRIFT_WARN_MS:
        logger.warning(
            f"[{msg_id}] ⚠ Clock drift detected | "
            f"sent_ts={sent_ts} | received_ts={received_ts} | "
            f"drift={clock_drift_ms:+,}ms ({clock_drift_ms/1000/60:.1f} min) | "
            f"device={payload['device_id']}"
        )

    # Data older than 15 minutes is treated as buffered replay
    # regardless of the is_buffered flag in the payload
    # (defensive: catches cases where device forgot to set the flag)
    is_old_buffered = clock_drift_ms > BUFFERED_CUTOFF_MS

    return clock_drift_ms, is_old_buffered


def _validate_schema(msg_id: str, payload: dict) -> None:
    version = payload.get('schema_version')
    if not version:
        raise ValueError(f"[{msg_id}] Missing 'schema_version' — cannot select validator")
    try:
        schema = get_schema(version)
    except ValueError:
        raise ValueError(f"[{msg_id}] Unknown schema_version '{version}' — no schema file found")
    try:
        validate(instance=payload, schema=schema)
    except ValidationError as e:
        field_path = ' -> '.join(str(p) for p in e.absolute_path) or 'root'
        raise ValueError(f"[{msg_id}] Schema validation failed at '{field_path}': {e.message}")


def _verify_device(msg_id: str, payload: dict):
    from apps.devices.models import Device
    device_id = payload['device_id']
    farm_id   = payload['farm_id']
    org_id    = payload['org_id']
    try:
        device = Device.objects.select_related('farm__organization').get(slug=device_id)
    except Device.DoesNotExist:
        raise ValueError(f"[{msg_id}] Auth failed — unknown device_id '{device_id}'")
    if device.status != Device.Status.ACTIVE:
        raise ValueError(f"[{msg_id}] Auth failed — device '{device_id}' is '{device.status}' (not active)")
    if device.farm.slug != farm_id:
        raise ValueError(f"[{msg_id}] Auth failed — device '{device_id}' belongs to farm '{device.farm.slug}', not claimed '{farm_id}' (possible spoofing)")
    if device.farm.organization.slug != org_id:
        raise ValueError(f"[{msg_id}] Auth failed — device '{device_id}' belongs to org '{device.farm.organization.slug}', not claimed '{org_id}' (possible spoofing)")
    return device