from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from logs.models import ActivityLog
from orders.models import Order
from departments.models import Department
from services.models import Service
from tickets.models import Message, Ticket
from tickets.services import (
    InvalidTransition,
    ResolvedTicketError,
    add_message,
    assign_main_expert,
    change_status,
    resolve,
)

User = get_user_model()


class WorkflowBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Работилница", slug="rabotilnica")
        cls.service = Service.objects.create(
            name="Услуга за работа",
            service_type=Service.ServiceType.ONE_TIME,
            price="40.00",
            department=cls.department,
        )
        cls.client_user = User.objects.create_user(
            username="klientche",
            password="Baceparola123",
            email="client@example.com",
            role=User.Role.CLIENT,
        )
        cls.expert = User.objects.create_user(
            username="expertche",
            password="Baceparola123",
            email="expert@example.com",
            role=User.Role.EXPERT,
        )
        order = Order.objects.create(
            user=cls.client_user,
            service=cls.service,
            amount="40.00",
            payment_method=Order.PaymentMethod.CARD,
            status=Order.Status.PAID,
        )
        cls.ticket = Ticket.objects.create(
            name="Проблемен тикет",
            order=order,
            client=cls.client_user,
            department=cls.department,
        )

    def _set_status(self, status):
        self.ticket.status = status
        self.ticket.save(update_fields=["status"])


class ChangeStatusTests(WorkflowBase):
    def test_open_to_in_progress_logs_and_emails(self):
        change_status(self.ticket, Ticket.Status.IN_PROGRESS, actor=self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)

        log = ActivityLog.objects.get(ticket=self.ticket)
        self.assertEqual(log.action, "status_change")
        self.assertEqual(log.actor, self.expert)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["client@example.com"])

    def test_waiting_reply_to_client_replied(self):
        self._set_status(Ticket.Status.WAITING_REPLY)
        change_status(self.ticket, Ticket.Status.CLIENT_REPLIED, actor=self.client_user)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLIENT_REPLIED)

    def test_client_replied_to_waiting_reply(self):
        self._set_status(Ticket.Status.CLIENT_REPLIED)
        change_status(self.ticket, Ticket.Status.WAITING_REPLY, actor=self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_REPLY)

    def test_open_to_resolved(self):
        change_status(self.ticket, Ticket.Status.RESOLVED, actor=self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)

    def test_self_transition_is_invalid(self):
        with self.assertRaises(InvalidTransition):
            change_status(self.ticket, Ticket.Status.OPEN, actor=self.expert)
        self.assertEqual(len(mail.outbox), 0)

    def test_unknown_status_is_invalid(self):
        with self.assertRaises(InvalidTransition):
            change_status(self.ticket, "teleport", actor=self.expert)


class TriggerTests(WorkflowBase):
    def test_assigning_expert_sets_in_progress(self):
        assign_main_expert(self.ticket, self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.main_expert, self.expert)
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertEqual(len(mail.outbox), 1)

    def test_assigning_expert_when_already_in_progress_does_not_re_notify(self):
        self._set_status(Ticket.Status.IN_PROGRESS)
        assign_main_expert(self.ticket, self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.main_expert, self.expert)
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(ActivityLog.objects.filter(ticket=self.ticket).count(), 0)

    def test_expert_message_sets_waiting_reply_and_last_message_at(self):
        self._set_status(Ticket.Status.IN_PROGRESS)
        message = add_message(self.ticket, self.expert, "Пробвай сега.")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_REPLY)
        self.assertEqual(self.ticket.last_message_at, message.created_at)
        self.assertFalse(message.is_internal)
        self.assertEqual(len(mail.outbox), 1)

    def test_internal_expert_message_does_not_change_status(self):
        self._set_status(Ticket.Status.IN_PROGRESS)
        add_message(self.ticket, self.expert, "Вътрешна бележка", is_internal=True)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertIsNone(self.ticket.last_message_at)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Message.objects.filter(ticket=self.ticket).count(), 1)

    def test_client_message_sets_client_replied_and_last_message_at(self):
        self._set_status(Ticket.Status.WAITING_REPLY)
        message = add_message(self.ticket, self.client_user, "Още не работи.")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLIENT_REPLIED)
        self.assertEqual(self.ticket.last_message_at, message.created_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_client_can_resolve(self):
        resolve(self.ticket, self.client_user)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        self.assertEqual(len(mail.outbox), 1)

    def test_expert_can_resolve(self):
        resolve(self.ticket, self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)


class ResolvedRestrictionTests(WorkflowBase):
    def setUp(self):
        self._set_status(Ticket.Status.RESOLVED)

    def test_client_cannot_change_status(self):
        with self.assertRaises(ResolvedTicketError):
            change_status(self.ticket, Ticket.Status.IN_PROGRESS, actor=self.client_user)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.RESOLVED)
        self.assertEqual(len(mail.outbox), 0)

    def test_client_cannot_add_message(self):
        with self.assertRaises(ResolvedTicketError):
            add_message(self.ticket, self.client_user, "Пак се счупи.")
        self.assertEqual(Message.objects.filter(ticket=self.ticket).count(), 0)

    def test_client_cannot_resolve_again(self):
        with self.assertRaises(ResolvedTicketError):
            resolve(self.ticket, self.client_user)

    def test_expert_can_reopen_via_message(self):
        message = add_message(self.ticket, self.expert, "Отварям пак.")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.WAITING_REPLY)
        self.assertEqual(Message.objects.filter(ticket=self.ticket).count(), 1)
        self.assertEqual(self.ticket.last_message_at, message.created_at)

    def test_expert_can_change_status(self):
        change_status(self.ticket, Ticket.Status.IN_PROGRESS, actor=self.expert)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)
