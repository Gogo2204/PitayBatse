from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class HomeRedirectTests(TestCase):
    def test_anonymous_redirected_to_services(self):
        response = self.client.get("/")
        self.assertRedirects(
            response, reverse("services:list"), fetch_redirect_response=False
        )

    def test_authenticated_redirected_to_dashboard(self):
        user = User.objects.create_user(username="nachalo", password="Baceparola123")
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertRedirects(
            response, reverse("accounts:dashboard"), fetch_redirect_response=False
        )
