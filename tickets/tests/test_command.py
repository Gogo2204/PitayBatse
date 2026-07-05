from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from departments.models import Department
from logs.models import ActivityLog
from orders.models import Order
from services.models import Service
from tickets.models import Ticket

User = get_user_model()


class CheckInactiveTicketsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Отдел ноктурно", slug="nokturno")
        cls.service = Service.objects.create(
            name="Услуга неактивност",
            service_type=Service.ServiceType.ONE_TIME,
            price="15.00",
            department=cls.department,
        )
        cls.client_user = User.objects.create_user(
            username="klientinactive",
            password="Baceparola123",
            email="client@example.com",
            role=User.Role.CLIENT,
        )

    def _ticket(self, status, last_message_offset_hours):
        order = Order.objects.create(
            user=self.client_user,
            service=self.service,
            amount=self.service.price,
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        ticket = Ticket.objects.create(
            name="Заспал тикет",
            order=order,
            client=self.client_user,
            department=self.department,
            status=status,
        )
        if last_message_offset_hours is not None:
            ticket.last_message_at = timezone.now() - timedelta(
                hours=last_message_offset_hours
            )
            ticket.save(update_fields=["last_message_at"])
        return ticket

    def test_stale_waiting_reply_is_reopened(self):
        ticket = self._ticket(Ticket.Status.WAITING_REPLY, 49)
        call_command("check_inactive_tickets")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.OPEN)

    def test_stale_in_progress_is_reopened(self):
        ticket = self._ticket(Ticket.Status.IN_PROGRESS, 72)
        call_command("check_inactive_tickets")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.OPEN)

    def test_recent_ticket_is_left_alone(self):
        ticket = self._ticket(Ticket.Status.WAITING_REPLY, 2)
        call_command("check_inactive_tickets")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.WAITING_REPLY)

    def test_other_statuses_are_ignored(self):
        resolved = self._ticket(Ticket.Status.RESOLVED, 200)
        client_replied = self._ticket(Ticket.Status.CLIENT_REPLIED, 200)
        call_command("check_inactive_tickets")
        resolved.refresh_from_db()
        client_replied.refresh_from_db()
        self.assertEqual(resolved.status, Ticket.Status.RESOLVED)
        self.assertEqual(client_replied.status, Ticket.Status.CLIENT_REPLIED)

    def test_ticket_without_last_message_is_skipped(self):
        ticket = self._ticket(Ticket.Status.IN_PROGRESS, None)
        call_command("check_inactive_tickets")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)

    def test_reopen_notifies_client_and_logs_system_action(self):
        self._ticket(Ticket.Status.WAITING_REPLY, 60)
        call_command("check_inactive_tickets")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["client@example.com"])

        log = ActivityLog.objects.filter(action="status_change").latest("created_at")
        self.assertIsNone(log.actor)

    @override_settings(TICKET_INACTIVITY_HOURS=1)
    def test_respects_configurable_interval(self):
        stale = self._ticket(Ticket.Status.WAITING_REPLY, 2)
        fresh = self._ticket(Ticket.Status.WAITING_REPLY, 0)
        call_command("check_inactive_tickets")
        stale.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(stale.status, Ticket.Status.OPEN)
        self.assertEqual(fresh.status, Ticket.Status.WAITING_REPLY)
