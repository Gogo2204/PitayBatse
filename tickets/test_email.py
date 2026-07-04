from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from departments.models import Department
from orders.models import Order
from services.models import Service
from tickets.models import Ticket
from tickets.services import ALLOWED_TRANSITIONS, change_status

User = get_user_model()


class StatusChangeEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Имейл отдел", slug="imejl-otdel")
        cls.service = Service.objects.create(
            name="Услуга имейл",
            service_type=Service.ServiceType.ONE_TIME,
            price="10.00",
            department=cls.department,
        )
        cls.client_user = User.objects.create_user(
            username="klientmail",
            password="Baceparola123",
            email="client@example.com",
            role=User.Role.CLIENT,
        )
        cls.expert = User.objects.create_user(
            username="ekspertmail",
            password="Baceparola123",
            email="expert@example.com",
            role=User.Role.EXPERT,
            department=cls.department,
        )

    def _ticket(self, status):
        order = Order.objects.create(
            user=self.client_user,
            service=self.service,
            amount=self.service.price,
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        return Ticket.objects.create(
            name="Имейл тикет",
            order=order,
            client=self.client_user,
            department=self.department,
            status=status,
        )

    def test_email_sent_on_every_transition_type(self):
        for from_status, targets in ALLOWED_TRANSITIONS.items():
            for to_status in targets:
                with self.subTest(from_status=from_status, to_status=to_status):
                    mail.outbox.clear()
                    ticket = self._ticket(from_status)

                    change_status(ticket, to_status, actor=self.expert)

                    self.assertEqual(len(mail.outbox), 1)
                    message = mail.outbox[0]
                    self.assertEqual(message.to, ["client@example.com"])
                    self.assertIn(ticket.name, message.body)
                    self.assertIn(Ticket.Status(from_status).label, message.body)
                    self.assertIn(Ticket.Status(to_status).label, message.body)

    def test_email_includes_reason_when_provided(self):
        ticket = self._ticket(Ticket.Status.OPEN)
        mail.outbox.clear()
        change_status(
            ticket, Ticket.Status.IN_PROGRESS, actor=self.expert, reason="Тестова причина."
        )
        self.assertIn("Тестова причина.", mail.outbox[0].body)
