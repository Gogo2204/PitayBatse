import os

from django import forms
from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".txt",
    ".log",
    ".csv",
    ".zip",
    ".doc",
    ".docx",
}


def validate_upload(uploaded):
    if uploaded.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Файлът е твърде голям (максимум 5 MB).")
    extension = os.path.splitext(uploaded.name)[1].lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f"Недопустим тип файл: {extension or 'без разширение'}."
        )


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return single_clean(data, initial)


class TicketCreateForm(forms.Form):
    name = forms.CharField(max_length=200, label="Заглавие на тикета")
    description = forms.CharField(
        label="Описание на проблема",
        widget=forms.Textarea(attrs={"rows": 6}),
    )
    deadline = forms.DateTimeField(
        required=False,
        label="Краен срок (по избор)",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    attachments = MultipleFileField(
        required=False, label="Прикачи файл", validators=[validate_upload]
    )

    site_admin_url = forms.URLField(required=False, label="URL за админ панел")
    site_username = forms.CharField(
        required=False, max_length=255, label="Потребител за сайта"
    )
    site_password = forms.CharField(
        required=False,
        label="Парола за сайта",
        widget=forms.PasswordInput(render_value=False),
    )
    hosting_username = forms.CharField(
        required=False, max_length=255, label="Потребител за хостинг"
    )
    hosting_password = forms.CharField(
        required=False,
        label="Парола за хостинг",
        widget=forms.PasswordInput(render_value=False),
    )


class ReplyForm(forms.Form):
    body = forms.CharField(
        label="Съобщение",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    attachments = MultipleFileField(
        required=False, label="Прикачи файл", validators=[validate_upload]
    )


class ExpertReplyForm(ReplyForm):
    is_internal = forms.BooleanField(required=False, label="Бележка")
