from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "service_type", "price", "department", "is_active")
    list_filter = ("service_type", "is_active", "department")
    search_fields = ("name", "description")
