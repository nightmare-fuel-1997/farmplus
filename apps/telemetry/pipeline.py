import json
import logging

logger = logging.getLogger(__name__)


def run_pipeline(msg_id: str, fields: dict, redis_client) -> None:
    """
    The assembly line. Each step is called in order.
    If any step raises an exception, it propagates to tasks.py
    which catches it, logs it, and does NOT xack the message.

    Steps (added sprint by sprint):
        S3-2: JSON Schema Validation
        S3-3: Device Identity & Auth
        S3-4: Clock Drift Check
        S3-5: Routing Fork
        S3-6: TimescaleDB Write
    """
    # --- Parse the raw stream fields ---
    raw_payload  = fields.get('payload', '{}')
    topic        = fields.get('topic', '')
    received_ts  = int(fields.get('received_ts', 0))

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Unparseable JSON in stream entry {msg_id}: {e}")

    logger.info(
        f"[{msg_id}] Processing | device={payload.get('device_id')} "
        f"| buffered={payload.get('is_buffered')} "
        f"| topic={topic}"
    )

    # ----------------------------------------------------------------
    # STEP 1 — JSON Schema Validation         (S3-2, added next)
    # STEP 2 — Device Identity & Auth         (S3-3)
    # STEP 3 — Clock Drift Check              (S3-4)
    # STEP 4 — Routing Fork                   (S3-5)
    # STEP 5 — TimescaleDB Write              (S3-6)
    # ----------------------------------------------------------------

    # Temporary: just log what we received so we can verify the plumbing
    logger.info(
        f"[{msg_id}] ✓ Parsed OK | "
        f"temp={payload.get('readings', {}).get('temperature')}°C | "
        f"nh3={payload.get('readings', {}).get('nh3')}ppm"
    )