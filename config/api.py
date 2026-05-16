# config/api.py
from ninja import NinjaAPI
from apps.devices.api import devices_router, farms_router
from apps.telemetry.api import router as telemetry_router

api = NinjaAPI(
    title="FarmPulse API",
    version="1.0.0",
    description="IoT Chicken Farm Monitoring — Backend API",
)

api.add_router("/devices/",  devices_router,  tags=["Devices"])
api.add_router("/farms/",    farms_router,    tags=["Farms"])
api.add_router("/telemetry/", telemetry_router, tags=["Telemetry"])
