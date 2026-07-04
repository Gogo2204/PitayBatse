from django.contrib import admin

from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
