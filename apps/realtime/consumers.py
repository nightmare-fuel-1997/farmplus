
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class TelemetryConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.farm_id = self.scope["url_route"]["kwargs"]["farm_id"]
        # Channel group name — must be valid: use dots not colons
        self.group_name = f"farm.{self.farm_id}.live"

        # Join the channel group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()
        logger.info(f"[WS] Client connected → group='{self.group_name}'")

    async def disconnect(self, close_code):
        # Leave the channel group cleanly
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )
        logger.info(f"[WS] Client disconnected → group='{self.group_name}' code={close_code}")

    # Called when a message is received FROM the browser
    # We are read-only for now — dashboard only receives, never sends
    async def receive(self, text_data=None, bytes_data=None):
        pass

    # Called when pipeline.py publishes to this group via channel layer
    # The method name MUST match the type field in the message dict
    async def telemetry_message(self, event):
        await self.send(text_data=event["payload"])
        logger.debug(f"[WS] Forwarded message → group='{self.group_name}'")