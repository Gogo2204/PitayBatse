from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from departments.models import Department
from orders.models import Order
from services.models import Service
from tickets.models import Credential, Ticket

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
