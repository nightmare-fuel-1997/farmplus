# config/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.realtime.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Standard HTTP requests → Django handles as normal
    "http": get_asgi_application(),

    # WebSocket requests → routed to our consumers
    "websocket": AllowedHostsOriginValidator(
        URLRouter(websocket_urlpatterns)
    ),
})