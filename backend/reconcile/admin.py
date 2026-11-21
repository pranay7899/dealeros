from django.contrib import admin
from .models import Location, SystemARecord, SystemBEntry


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("location_id", "org_id", "name")
    list_filter = ("org_id",)
    search_fields = ("location_id", "org_id", "name")


@admin.register(SystemARecord)
class SystemARecordAdmin(admin.ModelAdmin):
    list_display = ("record_id", "location", "event_date", "category_code", "total_value", "state")
    list_filter = ("state", "category_code", "location__org_id")
    search_fields = ("record_id", "actor_id")


@admin.register(SystemBEntry)
class SystemBEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_id", "record_ref", "location", "recorded_on", "value", "label")
    list_filter = ("location__org_id",)
    search_fields = ("entry_id", "record_ref", "record_ref_raw")

