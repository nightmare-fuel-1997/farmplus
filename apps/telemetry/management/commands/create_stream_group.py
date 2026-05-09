from django.core.management.base import BaseCommand
from django.conf import settings
import redis


class Command(BaseCommand):
    help = 'Create the Redis Stream consumer group for the telemetry pipeline.'

    def handle(self, *args, **options):
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        stream = settings.TELEMETRY_REDIS_STREAM_KEY       # 'telemetry-stream'
        group  = settings.TELEMETRY_REDIS_CONSUMER_GROUP   # 'pipeline-workers'

        try:
            # MKSTREAM creates the stream if it doesn't exist yet
            r.xgroup_create(stream, group, id='0', mkstream=True)
            self.stdout.write(self.style.SUCCESS(
                f"Consumer group '{group}' created on stream '{stream}'."
            ))
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                # Group already exists — this is fine, not an error
                self.stdout.write(self.style.WARNING(
                    f"Consumer group '{group}' already exists. Nothing to do."
                ))
            else:
                raise