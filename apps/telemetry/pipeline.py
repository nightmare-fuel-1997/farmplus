# apps/telemetry/pipeline.py
import json
import logging
from jsonschema import validate, ValidationError

from .schemas import get_schema

logger = logging.getLogger(__name__)


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
    logger.info(f"[{msg_id}] ✓ Step 2 passed | device={device.slug} | farm={device.farm.slug}")

    # ----------------------------------------------------------------
    # STEP 3 — Clock Drift Check           (S3-4, next)
    # STEP 4 — Routing Fork                (S3-5)
    # STEP 5 — TimescaleDB Write           (S3-6)
    # ----------------------------------------------------------------


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
        raise ValueError(
            f"[{msg_id}] Schema validation failed at '{field_path}': {e.message}"
        )


def _verify_device(msg_id: str, payload: dict):
    """
    Query PostgreSQL to verify:
      1. device_id (slug) exists
      2. device status is 'active'
      3. device belongs to the claimed farm_id and org_id

    Returns the Device ORM instance on success (used by downstream steps).
    Raises ValueError on any auth failure — tasks.py will not XACK.

    Phase 9 note: the 'stolen' status check is already handled here —
    a stolen device has status != 'active' and is rejected automatically.
    """
    # Import here to avoid circular imports at module load time
    from apps.devices.models import Device

    device_id = payload['device_id']
    farm_id   = payload['farm_id']
    org_id    = payload['org_id']

    # Step 2a — does the device exist?
    try:
        device = Device.objects.select_related('farm__organization').get(slug=device_id)
    except Device.DoesNotExist:
        raise ValueError(
            f"[{msg_id}] Auth failed — unknown device_id '{device_id}'"
        )

    # Step 2b — is it active?
    if device.status != Device.Status.ACTIVE:
        raise ValueError(
            f"[{msg_id}] Auth failed — device '{device_id}' is '{device.status}' (not active)"
        )

    # Step 2c — does it belong to the claimed farm and org?
    if device.farm.slug != farm_id:
        raise ValueError(
            f"[{msg_id}] Auth failed — device '{device_id}' belongs to farm "
            f"'{device.farm.slug}', not claimed '{farm_id}' (possible spoofing)"
        )

    if device.farm.organization.slug != org_id:
        raise ValueError(
            f"[{msg_id}] Auth failed — device '{device_id}' belongs to org "
            f"'{device.farm.organization.slug}', not claimed '{org_id}' (possible spoofing)"
        )

    return device