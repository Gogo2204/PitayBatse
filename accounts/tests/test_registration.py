from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationTests(TestCase):
    def test_registration_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration_creates_client_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newclient",
                "email": "new@example.com",
                "password1": "Baceparola123",
                "password2": "Baceparola123",
            },
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))

        user = User.objects.get(username="newclient")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.role, User.Role.CLIENT)
        self.assertIn("_auth_user_id", self.client.session)

    def test_password_mismatch_shows_error_and_creates_no_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "baduser",
                "email": "bad@example.com",
                "password1": "Baceparola123",
                "password2": "Different456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="baduser").exists())
