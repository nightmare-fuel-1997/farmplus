from django.contrib import admin
from .models import Organization, Farm, Device

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "created_at"]

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "organization", "created_at"]

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "farm", "status", "firmware_version", "last_seen_at"]
    list_filter  = ["status"]