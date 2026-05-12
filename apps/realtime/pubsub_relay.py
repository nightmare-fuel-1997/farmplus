# apps/realtime/pubsub_relay.py
import asyncio
import json
import logging
import os
import sys
import django

# Bootstrap Django before importing anything else
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

import redis.asyncio as aioredis
from django.conf import settings
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PATTERN = "farm:*:live"   # subscribes to ALL farms at once


async def relay():
    channel_layer = get_channel_layer()
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async with client.pubsub() as pubsub:
        await pubsub.psubscribe(PATTERN)
        logger.info(f"[Relay] Subscribed to Redis PubSub pattern '{PATTERN}'")

        async for raw in pubsub.listen():
            # psubscribe sends a confirmation message first — skip it
            if raw["type"] != "pmessage":
                continue

            redis_channel = raw["channel"]   # e.g. "farm:farm01:live"
            data          = raw["data"]      # JSON string from pipeline.py

            # Convert Redis channel name → Channels group name
            # "farm:farm01:live" → "farm.farm01.live"
            group_name = redis_channel.replace(":", ".")

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"[Relay] Invalid JSON on channel '{redis_channel}' — skipped")
                continue

            # Forward to the Django Channels group
            # type "telemetry_message" maps to TelemetryConsumer.telemetry_message()
            await channel_layer.group_send(
                group_name,
                {
                    "type": "telemetry_message",
                    "payload": json.dumps(payload),
                }
            )
            logger.info(f"[Relay] → Forwarded to Channels group '{group_name}'")


if __name__ == "__main__":
    asyncio.run(relay())