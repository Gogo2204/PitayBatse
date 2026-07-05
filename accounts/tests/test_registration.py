from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationTests(TestCase):
    def _payload(self, **overrides):
        payload = {
            "username": "newclient",
            "first_name": "Иван",
            "last_name": "Петров",
            "email": "new@example.com",
            "password1": "Baceparola123",
            "password2": "Baceparola123",
        }
        payload.update(overrides)
        return payload

    def test_registration_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration_creates_client_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), self._payload())
        self.assertRedirects(response, reverse("accounts:dashboard"))

        user = User.objects.get(username="newclient")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.first_name, "Иван")
        self.assertEqual(user.last_name, "Петров")
        self.assertEqual(user.role, User.Role.CLIENT)
        self.assertIn("_auth_user_id", self.client.session)

    def test_password_mismatch_shows_error_and_creates_no_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(username="baduser", password2="Different456"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_names_are_required(self):
        response = self.client.post(
            reverse("accounts:register"),
            self._payload(username="noname", first_name="", last_name=""),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("first_name", form.errors)
        self.assertIn("last_name", form.errors)
        self.assertFalse(User.objects.filter(username="noname").exists())
