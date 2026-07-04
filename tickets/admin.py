from django import forms
from django.contrib import admin

from .models import Attachment, Credential, Message, Ticket

ENCRYPTED_FIELDS = (
    "site_username",
    "site_password",
    "hosting_username",
    "hosting_password",
)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("name", "public_id", "client", "department", "status", "priority", "created_at")
    list_filter = ("status", "priority", "department")
    search_fields = ("name", "public_id", "client__username")
    filter_horizontal = ("watchers",)
    readonly_fields = ("public_id", "created_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("body",)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "message", "uploaded_by", "uploaded_at")


class CredentialAdminForm(forms.ModelForm):
    class Meta:
        model = Credential
        fields = "__all__"
        widgets = {
            field: forms.PasswordInput(render_value=False) for field in ENCRYPTED_FIELDS
        }

    def clean(self):
        cleaned = super().clean()
        if self.instance and self.instance.pk:
            for field in ENCRYPTED_FIELDS:
                if not cleaned.get(field):
                    cleaned[field] = getattr(self.instance, field)
        return cleaned


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    form = CredentialAdminForm
    list_display = ("ticket", "site_admin_url")
