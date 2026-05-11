import logging
from celery import shared_task
from django.conf import settings
import redis

from .pipeline import run_pipeline

logger = logging.getLogger(__name__)

STREAM_KEY     = settings.TELEMETRY_REDIS_STREAM_KEY      # 'telemetry-stream'
CONSUMER_GROUP = settings.TELEMETRY_REDIS_CONSUMER_GROUP  # 'pipeline-workers'
CONSUMER_NAME  = 'celery-worker-1'   # unique per worker instance (Phase 12: use hostname)
BATCH_SIZE     = 10                  # messages per XREADGROUP call
BLOCK_MS       = 5000                # block for 5 seconds if stream is empty


@shared_task(name='telemetry.consume_stream', ignore_result=True)
def consume_stream():
    """
    Read a batch of messages from the Redis Stream and process each one
    through the pipeline. Called repeatedly by Celery beat (Phase 11)
    or triggered manually in development.
    """
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    # Read up to BATCH_SIZE undelivered messages from the stream
    results = r.xreadgroup(
        groupname=CONSUMER_GROUP,
        consumername=CONSUMER_NAME,
        streams={STREAM_KEY: '>'},   # '>' means: give me NEW, undelivered messages
        count=BATCH_SIZE,
        block=BLOCK_MS,
    )

    if not results:
        logger.debug("Stream empty. Nothing to process.")
        return

    # results = [('telemetry-stream', [(msg_id, {field: value, ...}), ...])]
    _, messages = results[0]

    for msg_id, fields in messages:
        try:
            run_pipeline(msg_id, fields, r)
            # XACK only on full success — this is the crash-safety guarantee
            r.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
            logger.info(f"[{msg_id}] ACKed successfully.")

        except Exception as e:
            # Do NOT xack — message stays in PEL for reclaim/inspection
            logger.error(f"[{msg_id}] Pipeline failed: {e}. Message left in PEL.")