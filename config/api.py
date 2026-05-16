# config/api.py
from ninja import NinjaAPI
from apps.devices.api import orgs_router, farms_router, devices_router
from apps.telemetry.api import router as telemetry_router

api = NinjaAPI(
    title="FarmPulse API",
    version="1.0.0",
    description="IoT Chicken Farm Monitoring Backend API",
)

api.add_router("/orgs",      orgs_router,      tags=["Organizations"])
api.add_router("/farms",     farms_router,      tags=["Farms"])
api.add_router("/devices",   devices_router,    tags=["Devices"])
api.add_router("/telemetry", telemetry_router,  tags=["Telemetry"])