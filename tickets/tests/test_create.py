import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from departments.models import Department
from orders.models import Order
from services.models import Service
from tickets.models import Attachment, Ticket

User = get_user_model()


class TicketCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Тикет отдел", slug="tiket-otdel")
        cls.one_time_service = Service.objects.create(
            name="Еднократна за тикет",
            service_type=Service.ServiceType.ONE_TIME,
            price="80.00",
            department=cls.department,
        )
        cls.subscription_service = Service.objects.create(
            name="Абонамент за тикет",
            service_type=Service.ServiceType.SUBSCRIPTION,
            price="25.00",
            department=cls.department,
        )
        cls.user = User.objects.create_user(username="klientka", password="Baceparola123")

    def _order(self, service, status=Order.Status.PAID, billing_cycle=None, user=None):
        return Order.objects.create(
            user=user or self.user,
            service=service,
            billing_cycle=billing_cycle,
            amount=service.price,
            payment_method=Order.PaymentMethod.CARD,
            status=status,
        )

    def _valid_payload(self, **overrides):
        payload = {
            "name": "Сайто ми е счупен",
            "site_url": "https://mysite.example.com",
            "description": "Нищо не работи, баце, оправи го.",
            "site_admin_url": "https://example.com/wp-admin",
            "site_username": "admin",
            "site_password": "tajna-parola",
            "hosting_username": "hostuser",
            "hosting_password": "host-tajna",
        }
        payload.update(overrides)
        return payload

    def test_requires_login(self):
        order = self._order(self.one_time_service)
        response = self.client.get(reverse("tickets:create", args=[order.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_get_form_for_paid_order(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        response = self.client.get(reverse("tickets:create", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Заглавие на тикета")

    def test_subscription_shows_billing_notice(self):
        self.client.force_login(self.user)
        order = self._order(
            self.subscription_service, billing_cycle=Order.BillingCycle.MONTHLY
        )
        response = self.client.get(reverse("tickets:create", args=[order.pk]))
        self.assertContains(response, "абонаментна услуга")
        self.assertContains(response, "Месечно")

    def test_unpaid_order_redirects_to_payment(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service, status=Order.Status.PENDING)
        response = self.client.get(reverse("tickets:create", args=[order.pk]))
        self.assertRedirects(
            response,
            reverse("orders:pay", args=[order.pk]),
            fetch_redirect_response=False,
        )

    def test_cannot_access_another_users_order(self):
        other = User.objects.create_user(username="chuzhd", password="Baceparola123")
        order = self._order(self.one_time_service, user=other)
        self.client.force_login(self.user)
        response = self.client.get(reverse("tickets:create", args=[order.pk]))
        self.assertEqual(response.status_code, 404)

    def test_post_creates_ticket_credential_and_first_message(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        response = self.client.post(
            reverse("tickets:create", args=[order.pk]), self._valid_payload()
        )
        ticket = Ticket.objects.get(order=order)
        self.assertRedirects(
            response, reverse("tickets:detail", args=[ticket.public_id])
        )

        self.assertEqual(ticket.status, Ticket.Status.OPEN)
        self.assertEqual(ticket.site_url, "https://mysite.example.com")
        self.assertEqual(ticket.department, self.department)
        self.assertEqual(ticket.client, self.user)
        self.assertIsNotNone(ticket.last_message_at)

        message = ticket.messages.get()
        self.assertEqual(message.body, "Нищо не работи, баце, оправи го.")
        self.assertEqual(message.author, self.user)
        self.assertFalse(message.is_internal)
        self.assertEqual(ticket.last_message_at, message.created_at)

        credential = ticket.credential
        self.assertEqual(credential.site_password, "tajna-parola")
        self.assertEqual(credential.hosting_username, "hostuser")

    def test_one_order_produces_only_one_ticket(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        self.client.post(
            reverse("tickets:create", args=[order.pk]), self._valid_payload()
        )
        ticket = Ticket.objects.get(order=order)

        response = self.client.get(reverse("tickets:create", args=[order.pk]))
        self.assertRedirects(
            response, reverse("tickets:detail", args=[ticket.public_id])
        )

        self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(name="Втори опит"),
        )
        self.assertEqual(Ticket.objects.filter(order=order).count(), 1)

    def test_deadline_accepts_a_date_only_value(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(deadline="2040-12-31"),
        )
        ticket = Ticket.objects.get(order=order)
        self.assertIsNotNone(ticket.deadline)
        self.assertEqual(
            timezone.localtime(ticket.deadline).date().isoformat(), "2040-12-31"
        )

    def test_site_url_is_required(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        response = self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(site_url=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("site_url", response.context["form"].errors)
        self.assertFalse(Ticket.objects.filter(order=order).exists())

    def test_subscription_order_allows_multiple_tickets(self):
        self.client.force_login(self.user)
        order = self._order(
            self.subscription_service, billing_cycle=Order.BillingCycle.MONTHLY
        )
        self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(name="Първи тикет"),
        )
        self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(name="Втори тикет"),
        )
        self.assertEqual(order.tickets.count(), 2)

    def test_post_with_attachment_creates_attachment(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        upload = SimpleUploadedFile(
            "screenshot.txt", b"greshka na ekrana", content_type="text/plain"
        )
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            self.client.post(
                reverse("tickets:create", args=[order.pk]),
                self._valid_payload(attachments=upload),
            )

        ticket = Ticket.objects.get(order=order)
        attachment = Attachment.objects.get(ticket=ticket)
        self.assertEqual(attachment.uploaded_by, self.user)
        self.assertEqual(attachment.message, ticket.messages.get())
        self.assertTrue(attachment.file.name.startswith("tickets/"))

    def test_oversized_attachment_is_rejected(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        big = SimpleUploadedFile(
            "huge.txt", b"x" * (5 * 1024 * 1024 + 1), content_type="text/plain"
        )
        response = self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(attachments=big),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(order=order).exists())

    def test_disallowed_extension_is_rejected(self):
        self.client.force_login(self.user)
        order = self._order(self.one_time_service)
        bad = SimpleUploadedFile(
            "virus.exe", b"malware", content_type="application/octet-stream"
        )
        response = self.client.post(
            reverse("tickets:create", args=[order.pk]),
            self._valid_payload(attachments=bad),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(order=order).exists())
