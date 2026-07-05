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

    def test_initials_fall_back_to_username_for_legacy_users(self):
        self.assertEqual(User(username="pesho").initials, "PE")


class ProfileViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="profil",
            password="Baceparola123",
            email="p@example.com",
            first_name="Стар",
            last_name="Профил",
        )

    def _payload(self, **overrides):
        payload = {
            "username": "profil",
            "email": "p@example.com",
            "first_name": "Стар",
            "last_name": "Профил",
        }
        payload.update(overrides)
        return payload

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_profile_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Информация")
        self.assertContains(response, "Парола")

    def test_saves_username_email_and_names(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:profile"),
            self._payload(
                username="novoime",
                email="new@example.com",
                first_name="Ново",
                last_name="Име",
            ),
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "novoime")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.first_name, "Ново")
        self.assertEqual(self.user.last_name, "Име")

    def test_upload_avatar(self):
        self.client.force_login(self.user)
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            response = self.client.post(
                reverse("accounts:profile"),
                self._payload(avatar=make_image()),
            )
            self.assertRedirects(response, reverse("accounts:profile"))
            self.user.refresh_from_db()
            self.assertTrue(self.user.avatar.name.startswith("avatars/"))

    def test_delete_avatar_checkbox_clears_it(self):
        self.client.force_login(self.user)
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            self.client.post(reverse("accounts:profile"), self._payload(avatar=make_image()))
            self.user.refresh_from_db()
            self.assertTrue(self.user.avatar)

            self.client.post(
                reverse("accounts:profile"), self._payload(delete_avatar="on")
            )
            self.user.refresh_from_db()
            self.assertFalse(self.user.avatar)

    def test_names_required(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:profile"),
            self._payload(first_name="", last_name=""),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["profile_form"]
        self.assertIn("first_name", form.errors)

    def test_non_image_avatar_rejected(self):
        self.client.force_login(self.user)
        bad = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
        response = self.client.post(
            reverse("accounts:profile"), self._payload(avatar=bad)
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)


class PasswordChangeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="parolar",
            password="Baceparola123",
            first_name="П",
            last_name="Р",
        )

    def test_requires_login(self):
        response = self.client.post(reverse("accounts:password_change"))
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
        self.assertIn("old_password", response.context["password_form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Baceparola123"))

    def test_password_change_succeeds_and_keeps_session(self):
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
        self.assertIn("_auth_user_id", self.client.session)
