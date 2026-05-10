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

    logger.info(
        f"[{msg_id}] ✓ Schema valid | "
        f"device={payload['device_id']} | "
        f"v={payload['schema_version']} | "
        f"buffered={payload['is_buffered']} | "
        f"temp={payload['readings']['temperature']}°C | "
        f"nh3={payload['readings'].get('nh3', 'N/A')}ppm"
    )

    # ----------------------------------------------------------------
    # STEP 2 — Device Identity & Auth      (S3-3, next)
    # STEP 3 — Clock Drift Check           (S3-4)
    # STEP 4 — Routing Fork                (S3-5)
    # STEP 5 — TimescaleDB Write           (S3-6)
    # ----------------------------------------------------------------


def _validate_schema(msg_id: str, payload: dict) -> None:
    """
    Load the correct schema by version, validate payload against it.
    Raises ValueError with a precise field path on failure.
    """
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