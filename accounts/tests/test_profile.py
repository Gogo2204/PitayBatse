import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

User = get_user_model()


def make_image(name="avatar.png"):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class InitialsTests(TestCase):
    def test_initials_from_username(self):
        self.assertEqual(User(username="pesho").initials, "PE")
        self.assertEqual(User(username="Иванчо").initials, "ИВ")


class ProfileViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="profil", password="Baceparola123", email="p@example.com"
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_profile_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "profil")

    def test_upload_avatar(self):
        self.client.force_login(self.user)
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            response = self.client.post(
                reverse("accounts:profile"),
                {
                    "username": "profil",
                    "email": "p@example.com",
                    "avatar": make_image(),
                },
            )
            self.assertRedirects(response, reverse("accounts:profile"))
            self.user.refresh_from_db()
            self.assertTrue(self.user.avatar.name.startswith("avatars/"))

    def test_only_username_email_avatar_saved(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "username": "novoime",
                "email": "new@example.com",
                "first_name": "Опит",
                "last_name": "Хак",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "novoime")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.first_name, "")
        self.assertEqual(self.user.last_name, "")

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="zaeto", password="Baceparola123")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:profile"),
            {"username": "zaeto", "email": "p@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profil")

    def test_non_image_avatar_rejected(self):
        self.client.force_login(self.user)
        bad = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            reverse("accounts:profile"),
            {"username": "profil", "email": "p@example.com", "avatar": bad},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)


class PasswordChangeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="parolar", password="Baceparola123"
        )

    def test_requires_login(self):
        response = self.client.get(reverse("accounts:password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_wrong_old_password_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "grshna-parola",
                "new_password1": "NovaBaceparola456",
                "new_password2": "NovaBaceparola456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Baceparola123"))

    def test_password_change_succeeds_with_old_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "Baceparola123",
                "new_password1": "NovaBaceparola456",
                "new_password2": "NovaBaceparola456",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaBaceparola456"))
