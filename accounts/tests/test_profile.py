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
    def test_initials_from_first_and_last_name(self):
        user = User(username="ivancho", first_name="Иван", last_name="Петров")
        self.assertEqual(user.initials, "ИП")

    def test_initials_from_first_name_only(self):
        user = User(username="ivancho", first_name="Иван")
        self.assertEqual(user.initials, "И")

    def test_initials_fall_back_to_username(self):
        user = User(username="pesho")
        self.assertEqual(user.initials, "PE")


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
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "email": "p@example.com",
                    "avatar": make_image(),
                },
            )
            self.assertRedirects(response, reverse("accounts:profile"))
            self.user.refresh_from_db()
            self.assertTrue(self.user.avatar.name.startswith("avatars/"))

    def test_edit_basic_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Ново", "last_name": "Име", "email": "new@example.com"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ново")
        self.assertEqual(self.user.email, "new@example.com")

    def test_non_image_avatar_rejected(self):
        self.client.force_login(self.user)
        bad = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "", "last_name": "", "email": "p@example.com", "avatar": bad},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)
