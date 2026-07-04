from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from orders.models import Order
from services.models import Service
from tickets.models import Ticket

User = get_user_model()


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Отдел табло", slug="otdel-tablo")
        cls.service = Service.objects.create(
            name="Услуга табло",
            service_type=Service.ServiceType.ONE_TIME,
            price="12.00",
            department=cls.department,
        )
        cls.client_a = User.objects.create_user(
            username="tabloa", password="Baceparola123", role=User.Role.CLIENT
        )
        cls.client_b = User.objects.create_user(
            username="tablob", password="Baceparola123", role=User.Role.CLIENT
        )
        cls.order_a = cls._order(cls.client_a)
        cls.order_b = cls._order(cls.client_b)
        cls.ticket_a = cls._ticket(cls.client_a, cls.order_a, "Тикет на А")
        cls.ticket_b = cls._ticket(cls.client_b, cls.order_b, "Тикет на Б")

    @classmethod
    def _order(cls, user):
        return Order.objects.create(
            user=user,
            service=cls.service,
            amount=cls.service.price,
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )

    @classmethod
    def _ticket(cls, user, order, name, status=Ticket.Status.OPEN):
        return Ticket.objects.create(
            name=name,
            order=order,
            client=user,
            department=cls.department,
            status=status,
        )

    def test_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_client_sees_only_own_tickets(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тикет на А")
        self.assertNotContains(response, "Тикет на Б")

    def test_client_sees_only_own_orders(self):
        other_service = Service.objects.create(
            name="Само за Б",
            service_type=Service.ServiceType.ONE_TIME,
            price="77.00",
            department=self.department,
        )
        Order.objects.create(
            user=self.client_b,
            service=other_service,
            amount="77.00",
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        self.client.force_login(self.client_a)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(response, "Услуга табло")
        self.assertNotContains(response, "Само за Б")

    def test_status_filter_limits_tickets(self):
        self._ticket(
            self.client_a,
            self._order(self.client_a),
            "Приключен на А",
            status=Ticket.Status.RESOLVED,
        )
        self.client.force_login(self.client_a)

        response = self.client.get(
            reverse("accounts:dashboard"), {"status": Ticket.Status.RESOLVED}
        )
        self.assertContains(response, "Приключен на А")
        self.assertNotContains(response, "Тикет на А")

    def test_invalid_status_filter_is_ignored(self):
        self.client.force_login(self.client_a)
        response = self.client.get(
            reverse("accounts:dashboard"), {"status": "teleport"}
        )
        self.assertContains(response, "Тикет на А")
