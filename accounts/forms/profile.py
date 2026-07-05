from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from ..models import User

MAX_AVATAR_SIZE = 2 * 1024 * 1024


class ProfileForm(forms.ModelForm):
    field_order = ["username", "email", "first_name", "last_name", "avatar"]

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "avatar"]
        labels = {
            "username": "Потребителско име",
            "email": "Електронна поща",
            "first_name": "Име",
            "last_name": "Фамилия",
            "avatar": "Снимка",
        }
        widgets = {"avatar": forms.FileInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size") and avatar.size > MAX_AVATAR_SIZE:
            raise forms.ValidationError("Снимката е твърде голяма (максимум 2 MB).")
        return avatar


class ProfilePasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Текуща парола"
        self.fields["new_password1"].label = "Нова парола"
        self.fields["new_password2"].label = "Потвърди новата парола"
