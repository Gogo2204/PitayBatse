from django import forms


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
    attachments = MultipleFileField(required=False, label="Файлове (по избор)")

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
