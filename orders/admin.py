from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "service",
        "billing_cycle",
        "amount",
        "payment_method",
        "status",
        "created_at",
        "paid_at",
    )
    list_filter = ("status", "payment_method", "billing_cycle")
    search_fields = ("user__username", "service__name")
    readonly_fields = ("created_at", "paid_at")
