from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "ticket", "created_at")
    list_filter = ("action",)
    search_fields = ("action", "description")
    readonly_fields = ("created_at",)
