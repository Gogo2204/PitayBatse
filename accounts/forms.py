from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Имейл")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Потребителско име"
        self.fields["password1"].label = "Парола"
        self.fields["password2"].label = "Повторете паролата"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.CLIENT
        if commit:
            user.save()
        return user
