from ninja import NinjaAPI
# http://localhost:8000/api/docs
api = NinjaAPI(
    title="FarmPulse API",
    version="1.0.0",
    description="IoT Chicken Farm Monitoring — Backend API",
)

# Register routers from each app
from apps.devices.api import router as devices_router
from apps.telemetry.api import router as telemetry_router

api.add_router("/devices/", devices_router, tags=["Devices"])
api.add_router("/telemetry/", telemetry_router, tags=["Telemetry"])

