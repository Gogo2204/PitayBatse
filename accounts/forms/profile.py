from django import forms

from ..models import User

MAX_AVATAR_SIZE = 2 * 1024 * 1024


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "avatar"]
        labels = {
            "first_name": "Име",
            "last_name": "Фамилия",
            "email": "Имейл",
            "avatar": "Профилна снимка",
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size") and avatar.size > MAX_AVATAR_SIZE:
            raise forms.ValidationError("Снимката е твърде голяма (максимум 2 MB).")
        return avatar
