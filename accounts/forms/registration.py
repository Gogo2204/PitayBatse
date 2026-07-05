from django import forms
from django.contrib.auth.forms import UserCreationForm

from ..models import User


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=150, label="Име")
    last_name = forms.CharField(required=True, max_length=150, label="Фамилия")
    email = forms.EmailField(required=True, label="Имейл")

    field_order = [
        "username",
        "first_name",
        "last_name",
        "email",
        "password1",
        "password2",
    ]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Потребителско име"
        self.fields["password1"].label = "Парола"
        self.fields["password2"].label = "Повторете паролата"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CLIENT
        if commit:
            user.save()
        return user
