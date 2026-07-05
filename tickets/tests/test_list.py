from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from departments.models import Department
from orders.models import Order
from services.models import Service
from tickets.models import Ticket

User = get_user_model()


class TicketListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Първи отдел", slug="parvi")
        cls.other_department = Department.objects.create(name="Втори отдел", slug="vtori")
        cls.service = Service.objects.create(
            name="Услуга списък",
            service_type=Service.ServiceType.ONE_TIME,
            price="20.00",
            department=cls.department,
        )
        cls.other_service = Service.objects.create(
            name="Услуга друга",
            service_type=Service.ServiceType.ONE_TIME,
            price="20.00",
            department=cls.other_department,
        )
        cls.client_a = User.objects.create_user(
            username="klienta", password="Baceparola123", role=User.Role.CLIENT
        )
        cls.client_b = User.objects.create_user(
            username="klientb", password="Baceparola123", role=User.Role.CLIENT
        )
        cls.expert = User.objects.create_user(
            username="ekspertlist",
            password="Baceparola123",
            role=User.Role.EXPERT,
            department=cls.department,
        )
        cls.ticket_a = cls._make_ticket(cls.client_a, cls.service, cls.department, "Тикет на А")
        cls.ticket_b = cls._make_ticket(cls.client_b, cls.other_service, cls.other_department, "Тикет на Б")

    @classmethod
    def _make_ticket(cls, client, service, department, name):
        order = Order.objects.create(
            user=client,
            service=service,
            amount=service.price,
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        return Ticket.objects.create(
            name=name, order=order, client=client, department=department
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("tickets:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_client_sees_only_own_tickets(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse("tickets:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тикет на А")
        self.assertNotContains(response, "Тикет на Б")

    def test_expert_sees_only_department_tickets(self):
        self.client.force_login(self.expert)
        response = self.client.get(reverse("tickets:index"))
        self.assertContains(response, "Тикет на А")
        self.assertNotContains(response, "Тикет на Б")

    def test_empty_state_links_to_services(self):
        lonely = User.objects.create_user(
            username="sam", password="Baceparola123", role=User.Role.CLIENT
        )
        self.client.force_login(lonely)
        response = self.client.get(reverse("tickets:index"))
        self.assertContains(response, "няма тикети")
        self.assertContains(response, reverse("services:list"))
