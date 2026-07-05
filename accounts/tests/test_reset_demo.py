import os
import tempfile
from io import BytesIO, StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from services.models import Service
from tickets.models import Attachment, Message, Ticket

User = get_user_model()


def png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


class ResetDemoTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", password="Baceparola123"
        )
        self.department = Department.objects.create(name="Отдел", slug="otdel")
        self.service = Service.objects.create(
            name="Услуга",
            service_type=Service.ServiceType.ONE_TIME,
            price="10.00",
            department=self.department,
        )
        self.client_user = User.objects.create_user(
            username="klient", password="Baceparola123"
        )
        self.order = Order.objects.create(
            user=self.client_user,
            service=self.service,
            amount="10.00",
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        self.ticket = Ticket.objects.create(
            name="Тикет",
            site_url="https://example.com",
            order=self.order,
            client=self.client_user,
            department=self.department,
        )
        self.message = Message.objects.create(
            ticket=self.ticket, author=self.client_user, body="Здрасти"
        )
        ActivityLog.objects.create(action="test", description="нещо")

    def test_yes_flag_resets_demo_data(self):
        call_command("reset_demo", yes=True, stdout=StringIO())

        # Superusers survive.
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())
        # Regular users, tickets, orders, messages and logs are gone.
        self.assertFalse(User.objects.filter(username="klient").exists())
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(ActivityLog.objects.count(), 0)
        # Services and departments are untouched.
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    @patch("builtins.input", return_value="n")
    def test_prompt_abort_keeps_everything(self, mock_input):
        call_command("reset_demo", stdout=StringIO())
        self.assertTrue(User.objects.filter(username="klient").exists())
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(ActivityLog.objects.count(), 1)

    @patch("builtins.input", return_value="y")
    def test_prompt_confirm_resets(self, mock_input):
        call_command("reset_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(username="klient").exists())
        self.assertEqual(Ticket.objects.count(), 0)

    def test_removes_orphaned_attachment_and_avatar_files(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            attachment = Attachment.objects.create(
                ticket=self.ticket,
                message=self.message,
                uploaded_by=self.client_user,
                file=SimpleUploadedFile("bug.txt", b"stack trace"),
            )
            self.client_user.avatar = SimpleUploadedFile("me.png", png_bytes())
            self.client_user.save()

            attachment_path = attachment.file.path
            avatar_path = self.client_user.avatar.path
            self.assertTrue(os.path.exists(attachment_path))
            self.assertTrue(os.path.exists(avatar_path))

            call_command("reset_demo", yes=True, stdout=StringIO())

            self.assertFalse(os.path.exists(attachment_path))
            self.assertFalse(os.path.exists(avatar_path))
