import tempfile

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from departments.models import Department
from orders.models import Order
from services.models import Service
from tickets.models import Attachment, Credential, Message, Ticket

User = get_user_model()


class EncryptedFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name="Достъп отдел", slug="dostap-otdel")
        service = Service.objects.create(
            name="Услуга за тикет",
            service_type=Service.ServiceType.ONE_TIME,
            price="10.00",
            department=department,
        )
        cls.client_user = User.objects.create_user(
            username="klient", password="Baceparola123"
        )
        order = Order.objects.create(
            user=cls.client_user,
            service=service,
            amount="10.00",
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        cls.ticket = Ticket.objects.create(
            name="Тестов тикет",
            order=order,
            client=cls.client_user,
            department=department,
        )

    def test_round_trip_returns_plaintext(self):
        Credential.objects.create(
            ticket=self.ticket,
            site_admin_url="https://example.com/wp-admin",
            site_username="admin",
            site_password="s3cret-парола",
            hosting_username="hostuser",
            hosting_password="hostpass-123",
        )

        reloaded = Credential.objects.get(ticket=self.ticket)
        self.assertEqual(reloaded.site_username, "admin")
        self.assertEqual(reloaded.site_password, "s3cret-парола")
        self.assertEqual(reloaded.hosting_username, "hostuser")
        self.assertEqual(reloaded.hosting_password, "hostpass-123")

    def test_database_stores_ciphertext_not_plaintext(self):
        credential = Credential.objects.create(
            ticket=self.ticket,
            site_password="super-tajna",
            hosting_password="druga-tajna",
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT site_password, hosting_password "
                "FROM tickets_credential WHERE id = %s",
                [credential.id],
            )
            raw_site, raw_hosting = cursor.fetchone()

        self.assertNotEqual(raw_site, "super-tajna")
        self.assertNotIn("super-tajna", raw_site)
        self.assertNotEqual(raw_hosting, "druga-tajna")

        key = settings.FERNET_KEY
        fernet = Fernet(key.encode() if isinstance(key, str) else key)
        self.assertEqual(fernet.decrypt(raw_site.encode()).decode(), "super-tajna")
        self.assertEqual(fernet.decrypt(raw_hosting.encode()).decode(), "druga-tajna")

    def test_blank_values_are_preserved_as_blank(self):
        credential = Credential.objects.create(ticket=self.ticket)

        reloaded = Credential.objects.get(pk=credential.pk)
        self.assertEqual(reloaded.site_username, "")
        self.assertEqual(reloaded.site_password, "")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT site_username FROM tickets_credential WHERE id = %s",
                [credential.id],
            )
            (raw_username,) = cursor.fetchone()
        self.assertEqual(raw_username, "")

    def test_updating_value_reencrypts(self):
        credential = Credential.objects.create(
            ticket=self.ticket, site_password="staro"
        )
        credential.site_password = "novo"
        credential.save()

        self.assertEqual(
            Credential.objects.get(pk=credential.pk).site_password, "novo"
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT site_password FROM tickets_credential WHERE id = %s",
                [credential.id],
            )
            (raw,) = cursor.fetchone()
        self.assertNotIn("novo", raw)
        self.assertNotIn("staro", raw)


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
