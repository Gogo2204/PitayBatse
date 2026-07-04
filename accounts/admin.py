from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "department", "is_staff", "is_superuser")
    list_filter = UserAdmin.list_filter + ("role", "department")
    fieldsets = UserAdmin.fieldsets + (
        ("Роля и отдел", {"fields": ("role", "department")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Роля и отдел", {"fields": ("role", "department")}),
    )
